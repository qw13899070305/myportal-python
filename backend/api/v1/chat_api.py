"""聊天记录接口（HTTP）。

实时消息走 ``/api/v1/chat/ws``（原生 WebSocket）或
``/ws/socket.io``（socket.io），这里只负责历史记录的读写。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.security import get_current_user, is_admin
from backend.core.utils import utcnow
from backend.managers.connection import manager
from backend.models.chat import ChatMessage
from backend.models.user import User
from backend.schemas.chat import ChatMessageListOut
from backend.schemas.common import Message

router = APIRouter()


@router.get("/history", response_model=ChatMessageListOut)
async def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    size: int | None = Query(default=None, ge=1, le=200),
    page_size: int | None = Query(default=None, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """分页获取聊天历史（返回按时间正序排列的一段）。

    同时兼容 ``limit`` / ``size`` / ``page_size`` 三个参数名。
    """
    return await _history(page, size or limit or page_size or 50, db)


@router.get("/messages", response_model=ChatMessageListOut)
async def get_messages(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    size: int | None = Query(default=None, ge=1, le=200),
    page_size: int | None = Query(default=None, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """聊天历史（前端使用的路径，等价于 ``/history``）。"""
    return await _history(page, size or limit or page_size or 50, db)


async def _history(page: int, size: int, db: AsyncSession) -> ChatMessageListOut:
    base = select(ChatMessage).where(ChatMessage.is_recalled.is_(False))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    result = await db.execute(
        base.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    # 倒序取出后翻正，保证前端拼接顺序正确
    items = list(reversed(result.scalars().all()))
    return ChatMessageListOut(total=total, items=items)


@router.delete("/messages/{message_id}", response_model=Message)
async def recall_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """撤回自己的消息（超过时限后仅管理员可撤回）。"""
    message = await db.get(ChatMessage, message_id)
    if message is None or message.is_recalled:
        raise HTTPException(status_code=404, detail="消息不存在")
    if message.user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="只能撤回自己的消息")

    elapsed_minutes = (utcnow() - message.created_at).total_seconds() / 60
    if elapsed_minutes > settings.CHAT_RECALL_WINDOW_MINUTES and not is_admin(current_user):
        raise HTTPException(
            status_code=400,
            detail=f"超过 {settings.CHAT_RECALL_WINDOW_MINUTES} 分钟的消息无法撤回",
        )

    message.is_recalled = True
    db.add(message)
    await db.commit()

    await manager.broadcast({"type": "message_recalled", "id": message_id})
    logger.info(f"用户 {current_user.username} 撤回消息 #{message_id}")
    return Message(message="消息已撤回")


@router.delete("/messages", response_model=Message)
async def clear_my_messages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清空自己的聊天记录（管理员清空全部请用 ``/admin/chat/clear``）。"""
    result = await db.execute(select(ChatMessage).where(ChatMessage.user_id == current_user.id))
    messages = result.scalars().all()
    for message in messages:
        await db.delete(message)
    await db.commit()
    return Message(message=f"已清空 {len(messages)} 条消息")


@router.delete("/all", response_model=Message)
async def clear_all_messages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清空全部聊天记录（仅管理员）。"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="权限不足")
    await db.execute(delete(ChatMessage))
    await db.commit()
    await manager.broadcast({"type": "chat_cleared"})
    return Message(message="聊天记录已清空")


@router.get("/online")
async def online_users(_: User = Depends(get_current_user)):
    """当前在线的用户数量。"""
    return {"count": manager.online_count, "user_ids": manager.online_user_ids}
