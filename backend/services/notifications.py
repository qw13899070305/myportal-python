"""站内通知服务：所有通知的产生都集中在这里。"""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Notification


async def notify(
    db: AsyncSession,
    *,
    user_id: int,
    type: str,
    content: str,
    from_user_id: int | None = None,
) -> Notification | None:
    """给指定用户写一条站内通知。

    - 自己触发自己时直接跳过（避免给自己发通知）
    - 不提交事务，由调用方统一 ``commit``
    """
    if from_user_id is not None and from_user_id == user_id:
        return None
    notification = Notification(
        user_id=user_id,
        from_user_id=from_user_id,
        type=type,
        content=content,
    )
    db.add(notification)
    return notification
