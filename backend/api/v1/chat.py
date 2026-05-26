import json
import logging
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from backend.core.database import AsyncSessionLocal, get_db
from backend.core.security import get_current_user, verify_token
from backend.core.config import settings
from backend.models.user import User
from backend.models.chat import ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter()

_ws_connections: dict[str, int] = {}
_MAX_WS_CONN_PER_IP = 5


@router.get("/messages")
async def get_messages(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total = await db.scalar(select(func.count()).select_from(ChatMessage))
    stmt = select(ChatMessage).order_by(ChatMessage.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    messages = result.scalars().all()
    items = [
        {
            "id": m.id,
            "user_id": m.user_id,
            "username": m.user.username if m.user else "未知",
            "content": m.content,
            "created_at": m.created_at.isoformat()
        }
        for m in reversed(messages)
    ]
    return {"total": total, "items": items}


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    client_ip = websocket.client.host if websocket.client else "unknown"
    if _ws_connections.get(client_ip, 0) >= _MAX_WS_CONN_PER_IP:
        await websocket.close(code=4003, reason="连接数过多，请稍后再试")
        return

    _ws_connections[client_ip] = _ws_connections.get(client_ip, 0) + 1
    try:
        await websocket.accept()
        data = await websocket.receive_text()
        auth_msg = json.loads(data)
        token = auth_msg.get("token")
        if not token:
            await websocket.close(code=4001, reason="缺少认证令牌")
            return

        payload = verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="无效令牌")
            return

        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            await websocket.close(code=4001, reason="无效令牌")
            return

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).options(selectinload(User.roles)).where(User.id == user_id_int)
            )
            user = result.scalar_one_or_none()
            if not user:
                await websocket.close(code=4001, reason="用户不存在")
                return

            while True:
                raw = await websocket.receive_text()
                msg_data = json.loads(raw)
                content = msg_data.get("content", "").strip()
                if not content or len(content) > settings.CHAT_MESSAGE_MAX_LENGTH:
                    continue

                new_msg = ChatMessage(user_id=user.id, content=content)
                db.add(new_msg)
                await db.commit()
                await db.refresh(new_msg)

                response = {
                    "type": "message",
                    "id": new_msg.id,
                    "user_id": new_msg.user_id,
                    "username": user.username,
                    "content": new_msg.content,
                    "created_at": new_msg.created_at.isoformat()
                }
                await websocket.send_text(json.dumps(response))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("WebSocket error")
        await websocket.close(code=4000, reason="服务器内部错误")
    finally:
        _ws_connections[client_ip] = max(0, _ws_connections.get(client_ip, 0) - 1)