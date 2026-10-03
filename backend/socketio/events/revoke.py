"""撤回消息事件：``revoke_message`` -> 广播 ``message_revoked``。

超过撤回时限后仅管理员可撤回。时间为 naive UTC，两边可以直接相减。
"""

from __future__ import annotations

from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.core.utils import utcnow
from backend.models.chat import ChatMessage
from backend.models.user import User
from backend.socketio.server import sio


def _is_admin(user: User | None) -> bool:
    return bool(user and {"admin", "super_admin"} & set(user.role_names))


@sio.event
async def revoke_message(sid, data):
    """撤回自己的消息。"""
    session = await sio.get_session(sid)
    user_id = (session or {}).get("user_id")
    if not user_id or not isinstance(data, dict):
        return {"ok": False}

    try:
        msg_id = int(data.get("id"))
    except (TypeError, ValueError):
        return {"ok": False, "detail": "消息 id 不合法"}

    async with AsyncSessionLocal() as db:
        message = await db.get(ChatMessage, msg_id)
        if message is None or message.user_id != user_id:
            return {"ok": False, "detail": "消息不存在或无权撤回"}

        elapsed_minutes = (utcnow() - message.created_at).total_seconds() / 60
        if elapsed_minutes > settings.CHAT_RECALL_WINDOW_MINUTES:
            sender = await db.get(User, user_id)
            if not _is_admin(sender):
                return {"ok": False, "detail": "超过撤回时限"}

        message.is_recalled = True
        db.add(message)
        await db.commit()

    await sio.emit("message_revoked", {"id": msg_id})
    return {"ok": True}
