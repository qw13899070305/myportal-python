"""后台 · 聊天管理（可拆卸扩展）。

挂载在 ``/api/v1/admin`` 下：

- ``GET    /admin/chat/messages``        全部聊天记录（含已撤回）
- ``DELETE /admin/chat/clear``           清空全部记录（前端路径）
- ``DELETE /admin/chat/messages``        清空全部记录（REST 风格别名）
- ``DELETE /admin/chat/messages/{id}``   删除单条

把本文件删掉，聊天功能本身照常工作，只是没有后台管理入口。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.security import RoleChecker
from backend.models.chat import ChatMessage
from backend.models.user import User
from backend.schemas.chat import ChatMessageListOut
from backend.schemas.common import Message
from backend.services.audit import safe_log_action

router = APIRouter()

admin_only = RoleChecker(["admin", "super_admin"])


@router.get("/chat/messages", response_model=ChatMessageListOut)
async def admin_list_messages(
    page: int = Query(1, ge=1),
    size: int = Query(settings.PAGE_SIZE_DEFAULT, ge=1, le=settings.PAGE_SIZE_MAX),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
):
    """全部聊天记录（含已撤回）。"""
    total = await db.scalar(select(func.count()).select_from(ChatMessage)) or 0
    result = await db.execute(
        select(ChatMessage)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return ChatMessageListOut(total=total, items=result.scalars().all())


async def _clear_all(request: Request, db: AsyncSession, current_admin: User) -> Message:
    await db.execute(delete(ChatMessage))
    await db.commit()
    await safe_log_action(
        db,
        action="chat_clear",
        user_id=current_admin.id,
        detail="清空全部聊天记录",
        request=request,
    )
    logger.warning(f"管理员 {current_admin.username} 清空了全部聊天记录")
    return Message(message="聊天记录已清空")


@router.delete("/chat/clear", response_model=Message)
async def admin_clear_messages(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(admin_only),
):
    """清空所有聊天记录（前端使用的路径）。"""
    return await _clear_all(request, db, current_admin)


@router.delete("/chat/messages", response_model=Message)
async def admin_clear_messages_alias(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(admin_only),
):
    """清空所有聊天记录（REST 风格别名）。"""
    return await _clear_all(request, db, current_admin)


@router.delete("/chat/messages/{message_id}", response_model=Message)
async def admin_delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
):
    """删除单条聊天记录。"""
    message = await db.get(ChatMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="消息不存在")
    await db.delete(message)
    await db.commit()
    return Message(message="消息已删除")
