from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.chat import Notification

router = APIRouter(prefix="/notifications", tags=["通知"])

@router.get("/")
async def list_noti(unread_only: bool = False, page: int = Query(1, ge=1),
                    db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)
    stmt = stmt.order_by(Notification.created_at.desc()).offset((page-1)*20).limit(20)
    result = await db.execute(stmt)
    return [{"id": n.id, "type": n.type, "content": n.content, "is_read": n.is_read, "time": str(n.created_at)} for n in result.scalars().all()]

@router.post("/read-all")
async def read_all(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    await db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True))
    await db.commit()
    return {"ok": True}
