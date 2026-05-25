import re
import jwt
from core.config import SECRET_KEY, JWT_ALGORITHM
from datetime import datetime, timedelta
import socketio
import jwt
from core.config import SECRET_KEY, JWT_ALGORITHM
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.models.chat import ChatMessage, Notification
from backend.models.user import User
from sqlalchemy import select, func, delete

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
connected_users = {}

@sio.event
async def connect(sid, environ):
        token = environ.get("HTTP_AUTHORIZATION", "").replace("Bearer ", "")
        if not token:
            raise ConnectionRefusedError("authentication failed")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            user_id = payload["sub"]
            # 将 user_id 与 sid 绑定到 session
            sio.save_session(sid, {"user_id": user_id})
        except jwt.PyJWTError:
            raise ConnectionRefusedError("invalid token")
    pass

@sio.event
async def join(sid, data):
    user_id = data.get("user_id")
    if user_id:
        connected_users[sid] = user_id
        await sio.emit("user_joined", {"user_id": user_id}, skip_sid=sid)

@sio.event
async def send_message(sid, data):
    user_id = connected_users.get(sid)
    if not user_id:
        return
    content = data.get("content", "").strip()
    if not content:
        return

    async with AsyncSessionLocal() as db:
        msg = ChatMessage(user_id=user_id, content=content)
        db.add(msg)
        # 保留最近200条
        total = await db.scalar(select(func.count(ChatMessage.id)))
        if total > settings.CHAT_MAX_MESSAGES:
            over = total - settings.CHAT_MAX_MESSAGES
            subq = select(ChatMessage.id).order_by(ChatMessage.created_at.asc()).limit(over)
            await db.execute(delete(ChatMessage).where(ChatMessage.id.in_(subq)))
        await db.commit()

        # @提及通知
        mentions = re.findall(r'@(\w+)', content)
        for m_username in set(mentions):
            m_user = await db.execute(select(User).where(User.username == m_username))
            m_user = m_user.scalar_one_or_none()
            if m_user and m_user.id != user_id:
                notif = Notification(
                    user_id=m_user.id,
                    from_user_id=user_id,
                    type="mention",
                    content=f"{ (await db.get(User, user_id)).username } 在聊天中@了你"
                )
                db.add(notif)
        await db.commit()

        user = await db.get(User, user_id)
        username = user.username if user else "未知"
        payload = {
            "id": msg.id,
            "user_id": user_id,
            "username": username,
            "content": content,
            "time": str(msg.created_at)
        }
    # 广播给所有人
    await sio.emit("chat_message", payload)

@sio.event
async def revoke_message(sid, data):
    user_id = connected_users.get(sid)
    msg_id = data.get("id")
    async with AsyncSessionLocal() as db:
        msg = await db.get(ChatMessage, msg_id)
        if msg and msg.user_id == user_id:
            if datetime.utcnow() - msg.created_at < timedelta(minutes=settings.CHAT_RECALL_WINDOW_MINUTES):
                msg.is_recalled = True
                await db.commit()
                await sio.emit("message_revoked", {"id": msg_id})

@sio.event
async def disconnect(sid):
    user_id = connected_users.pop(sid, None)
    if user_id:
        await sio.emit("user_left", {"user_id": user_id})
