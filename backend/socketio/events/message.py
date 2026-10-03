"""聊天消息事件：``send_message`` -> 广播 ``chat_message``。

流程：清洗 HTML -> 落库 -> 清理超额历史 -> 处理 @提及 -> 广播。
"""

from __future__ import annotations

import re

import bleach
from sqlalchemy import delete, func, select

from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.core.utils import utcnow
from backend.models.chat import ChatMessage
from backend.models.user import User, get_user_by_username
from backend.services.notifications import notify
from backend.socketio.server import sio

#: 支持中文、字母、数字、下划线与点的 @提及
MENTION_RE = re.compile(r"@([A-Za-z0-9_\u4e00-\u9fa5.-]{1,50})")


async def _prune_history(db) -> int:
    """超出上限时删除最旧的聊天记录，返回删除条数。"""
    total = await db.scalar(select(func.count()).select_from(ChatMessage)) or 0
    if total <= settings.CHAT_MAX_MESSAGES:
        return 0
    over = total - settings.CHAT_MAX_MESSAGES
    old_ids = (
        select(ChatMessage.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .limit(over)
    )
    await db.execute(delete(ChatMessage).where(ChatMessage.id.in_(old_ids)))
    return over


async def _notify_mentions(db, content: str, sender_id: int, sender_name: str) -> list[int]:
    """给被 @ 的用户写通知，返回被提及的用户 id。"""
    mentioned: list[int] = []
    for name in set(MENTION_RE.findall(content)):
        target = await get_user_by_username(db, name)
        if target is None or target.id == sender_id:
            continue
        await notify(
            db,
            user_id=target.id,
            from_user_id=sender_id,
            type="mention",
            content=f"{sender_name} 在聊天中提到了你",
        )
        mentioned.append(target.id)
    return mentioned


@sio.event
async def send_message(sid, data):
    """接收聊天消息：清洗 -> 落库 -> 处理 @提及 -> 广播。"""
    session = await sio.get_session(sid)
    user_id = (session or {}).get("user_id")
    if not user_id:
        return {"ok": False, "detail": "未认证"}

    if not isinstance(data, dict):
        return {"ok": False, "detail": "消息格式错误"}

    content = str(data.get("content", "")).strip()
    if not content:
        return {"ok": False, "detail": "消息不能为空"}
    if len(content) > settings.CHAT_MESSAGE_MAX_LENGTH:
        return {"ok": False, "detail": "消息过长"}

    # 去掉所有 HTML 标签，避免存储型 XSS
    content = bleach.clean(content, tags=[], strip=True)

    async with AsyncSessionLocal() as db:
        message = ChatMessage(user_id=user_id, content=content, created_at=utcnow())
        db.add(message)
        await db.flush()

        await _prune_history(db)

        sender = await db.get(User, user_id)
        username = sender.username if sender else "未知"
        mentioned_ids = await _notify_mentions(db, content, user_id, username)

        await db.commit()
        await db.refresh(message)

    await sio.emit(
        "chat_message",
        {
            "id": message.id,
            "user_id": user_id,
            "username": username,
            "content": content,
            "created_at": message.created_at.isoformat(),
            "time": str(message.created_at),
        },
    )

    for target_id in mentioned_ids:
        await sio.emit(
            "notification",
            {"type": "mention", "content": f"{username} 在聊天中提到了你"},
            room=f"user_{target_id}",
        )
    return {"ok": True, "id": message.id}
