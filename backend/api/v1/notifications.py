"""站内通知接口。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.chat import Notification
from backend.models.user import User
from backend.schemas.chat import NotificationListOut
from backend.schemas.common import Message

router = APIRouter()


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """未读通知数量（用于顶栏红点）。"""
    count = (
        await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == current_user.id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )
    return {"unread": count}


@router.get("/", response_model=NotificationListOut)
async def list_notifications(
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(settings.PAGE_SIZE_DEFAULT, ge=1, le=settings.PAGE_SIZE_MAX),
    limit: int | None = Query(default=None, ge=1, le=settings.PAGE_SIZE_MAX),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户的通知列表。"""
    if limit is not None:  # 兼容旧前端的 limit 参数
        size = limit

    conditions = [Notification.user_id == current_user.id]
    if unread_only:
        conditions.append(Notification.is_read.is_(False))

    total = await db.scalar(select(func.count()).select_from(Notification).where(*conditions)) or 0
    unread = (
        await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == current_user.id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )
    result = await db.execute(
        select(Notification)
        .where(*conditions)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return NotificationListOut(total=total, unread=unread, items=result.scalars().all())


@router.post("/read-all", response_model=Message)
async def read_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """把所有通知标记为已读。"""
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    return Message(message="已全部标记为已读")


@router.post("/{notification_id}/read", response_model=Message)
async def read_one(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将单条通知标记为已读。"""
    notification = await db.get(Notification, notification_id)
    if notification is None or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="通知不存在")

    notification.is_read = True
    db.add(notification)
    await db.commit()
    return Message(message="已标记为已读")


@router.delete("/{notification_id}", response_model=Message)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除单条通知。"""
    notification = await db.get(Notification, notification_id)
    if notification is None or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="通知不存在")

    await db.delete(notification)
    await db.commit()
    return Message(message="通知已删除")
