import os
import re
import bleach
from datetime import datetime, timedelta, timezone
import jwt
import socketio

from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.models.chat import ChatMessage, Notification
from backend.models.user import User
from sqlalchemy import select, func, delete

# 从环境变量读取允许的源，并进行强校验
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
# 确保每个源都不是通配符
if "*" in allowed_origins:
    raise ValueError("出于安全考虑，不允许使用通配符作为 CORS 来源")

redis_url = os.getenv("REDIS_URL", "")
if redis_url:
    mgr = socketio.AsyncRedisManager(redis_url)
    sio = socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=allowed_origins,
        client_manager=mgr
    )
else:
    sio = socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=allowed_origins
    )


@sio.event
async def connect(sid, environ):
    # 校验 Origin 头
    origin = environ.get("HTTP_ORIGIN") or environ.get("HTTP_REFERER", "")
    if origin and origin not in allowed_origins:
        raise ConnectionRefusedError("origin not allowed")

    token = environ.get("HTTP_AUTHORIZATION", "").replace("Bearer ", "")
    if not token:
        raise ConnectionRefusedError("authentication failed")
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload["sub"]
        # 使用 socket.io 的会话存储，代替全局字典
        await sio.save_session(sid, {"user_id": user_id})
    except jwt.PyJWTError:
        raise ConnectionRefusedError("invalid token")


@sio.event
async def join(sid, data):
    session = await sio.get_session(sid)
    user_id = session.get("user_id") if session else None
    if user_id:
        await sio.emit("user_joined", {"user_id": user_id}, skip_sid=sid)


@sio.event
async def send_message(sid, data):
    session = await sio.get_session(sid)
    user_id = session.get("user_id") if session else None
    if not user_id:
        return

    content = data.get("content", "").strip()
    if not content:
        return

    content = bleach.clean(content, tags=[], strip=True)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            msg = ChatMessage(user_id=user_id, content=content)
            db.add(msg)

            # 清理旧消息
            total = await db.scalar(select(func.count(ChatMessage.id)))
            if total > settings.CHAT_MAX_MESSAGES:
                over = total - settings.CHAT_MAX_MESSAGES
                subq = select(ChatMessage.id).order_by(
                    ChatMessage.created_at.asc()
                ).limit(over)
                await db.execute(
                    delete(ChatMessage).where(ChatMessage.id.in_(subq))
                )

            # @提及处理
            mentions = re.findall(r'@(\w+)', content)
            for m_username in set(mentions):
                m_user = await db.execute(
                    select(User).where(User.username == m_username)
                )
                m_user = m_user.scalar_one_or_none()
                if m_user and m_user.id != user_id:
                    notif = Notification(
                        user_id=m_user.id,
                        from_user_id=user_id,
                        type="mention",
                        content=f"{(await db.get(User, user_id)).username} 在聊天中@了你"
                    )
                    db.add(notif)

            user = await db.get(User, user_id)
            username = user.username if user else "未知"

        payload = {
            "id": msg.id,
            "user_id": user_id,
            "username": username,
            "content": content,
            "time": str(msg.created_at)
        }
        await sio.emit("chat_message", payload)


@sio.event
async def revoke_message(sid, data):
    session = await sio.get_session(sid)
    user_id = session.get("user_id") if session else None
    msg_id = data.get("id")
    async with AsyncSessionLocal() as db:
        msg = await db.get(ChatMessage, msg_id)
        if msg and msg.user_id == user_id:
            if datetime.now(timezone.utc) - msg.created_at.replace(tzinfo=timezone.utc) < timedelta(minutes=settings.CHAT_RECALL_WINDOW_MINUTES):
                msg.is_recalled = True
                await db.commit()
                await sio.emit("message_revoked", {"id": msg_id})