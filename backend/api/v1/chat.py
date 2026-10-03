"""实时聊天（原生 WebSocket）。

连接地址：``/api/v1/chat/ws?token=<access_token>``

浏览器无法在 WebSocket 握手时自定义请求头，因此令牌通过查询参数传递。
消息以 JSON 收发：

- 客户端发送 ``{"content": "..."}``，或 ``{"type": "ping"}`` 做心跳
- 服务端推送 ``{"type": "message", ...}`` / ``{"type": "user_joined", ...}``
  / ``{"type": "message_recalled", ...}`` / ``{"type": "error", ...}``
"""

import json
import re

from fastapi import APIRouter, HTTPException, Query, WebSocket
from sqlalchemy import delete, func, select

from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.core.logger import logger
from backend.core.security import load_user_from_token
from backend.core.utils import utcnow
from backend.managers.connection import manager
from backend.models.chat import ChatMessage
from backend.models.user import User, get_user_by_username
from backend.services.notifications import notify

router = APIRouter()

_MENTION_RE = re.compile(r"@([A-Za-z0-9_\u4e00-\u9fa5.-]{1,50})")

#: 自定义 WebSocket 关闭码
WS_UNAUTHORIZED = 4401


def serialize_message(message: ChatMessage, username: str) -> dict:
    """统一的聊天消息载荷。"""
    created = message.created_at or utcnow()
    return {
        "type": "message",
        "id": message.id,
        "user_id": message.user_id,
        "username": username,
        "content": message.content,
        "created_at": created.isoformat(),
        "time": str(created),
    }


async def persist_message(user_id: int, content: str) -> tuple[ChatMessage, list[int]]:
    """落库并处理 @提及，返回 (消息对象, 被提及的用户 id 列表)。"""
    mentioned_ids: list[int] = []
    async with AsyncSessionLocal() as db:
        message = ChatMessage(user_id=user_id, content=content, created_at=utcnow())
        db.add(message)
        await db.flush()

        # 控制历史总量：删除最旧的记录
        total = await db.scalar(select(func.count()).select_from(ChatMessage)) or 0
        if total > settings.CHAT_MAX_MESSAGES:
            over = total - settings.CHAT_MAX_MESSAGES
            old_ids = (
                select(ChatMessage.id)
                .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
                .limit(over)
            )
            await db.execute(delete(ChatMessage).where(ChatMessage.id.in_(old_ids)))

        # @提及 -> 站内通知
        sender = await db.get(User, user_id)
        sender_name = sender.username if sender else "有人"
        for name in set(_MENTION_RE.findall(content)):
            target = await get_user_by_username(db, name)
            if target is None or target.id == user_id:
                continue
            await notify(
                db,
                user_id=target.id,
                from_user_id=user_id,
                type="mention",
                content=f"{sender_name} 在聊天中提到了你",
            )
            mentioned_ids.append(target.id)

        await db.commit()
        await db.refresh(message)
    return message, mentioned_ids


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket, token: str | None = Query(default=None)):
    """实时聊天。令牌通过查询参数传递。"""
    await websocket.accept()

    if not token:
        await websocket.close(code=WS_UNAUTHORIZED, reason="缺少认证令牌")
        return

    try:
        async with AsyncSessionLocal() as db:
            user = await load_user_from_token(token, db)
            user_id, username = user.id, user.username
    except HTTPException as exc:
        await websocket.close(code=WS_UNAUTHORIZED, reason=str(exc.detail))
        return
    except Exception:
        logger.exception("WebSocket 认证失败")
        await websocket.close(code=WS_UNAUTHORIZED, reason="认证失败")
        return

    manager.register(user_id, websocket)
    await manager.send_personal(user_id, {"type": "online", "count": manager.online_count})
    await manager.broadcast(
        {"type": "user_joined", "user_id": user_id, "username": username},
        exclude_user_id=user_id,
    )

    try:
        while True:
            raw = await websocket.receive_text()

            # 兼容纯文本消息（老前端直接发字符串）
            content = ""
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                content = raw.strip()
                payload = None

            if isinstance(payload, dict):
                if payload.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue
                content = str(payload.get("content", "")).strip()

            if not content:
                continue
            if len(content) > settings.CHAT_MESSAGE_MAX_LENGTH:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "detail": (f"消息过长（最多 {settings.CHAT_MESSAGE_MAX_LENGTH} 字）"),
                        },
                        ensure_ascii=False,
                    )
                )
                continue

            message, mentioned_ids = await persist_message(user_id, content)
            await manager.broadcast(serialize_message(message, username))

            for target_id in mentioned_ids:
                await manager.send_personal(
                    target_id,
                    {
                        "type": "notification",
                        "content": f"{username} 在聊天中提到了你",
                    },
                )

    except Exception as exc:  # 含 WebSocketDisconnect
        logger.debug(f"用户 {user_id} 的 WebSocket 会话结束: {exc}")
    finally:
        manager.disconnect(user_id, websocket)
        await manager.broadcast({"type": "user_left", "user_id": user_id, "username": username})
