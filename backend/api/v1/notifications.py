from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.chat import Notification

router = APIRouter(prefix="/notifications", tags=["通知"])

@router.get("/")
async def list_notifications(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(50))
    notifs = result.scalars().all()
    return {"items": [{"id":n.id,"from":n.from_user.username,"type":n.type,"content":n.content,"is_read":n.is_read,"time":n.created_at} for n in notifs]}

@router.post("/read/{notif_id}")
async def mark_read(notif_id: int, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    n = await db.get(Notification, notif_id)
    if n and n.user_id == user.id:
        n.is_read = True
        await db.commit()
    return {"msg":"ok"}
