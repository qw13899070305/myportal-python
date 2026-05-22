from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.chat import ChatMessage

router = APIRouter(prefix="/chat", tags=["聊天记录"])

@router.get("/history")
async def get_history(page: int=1, limit: int=50, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    q = select(ChatMessage).where(ChatMessage.is_recalled == False).order_by(ChatMessage.created_at.desc())
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    messages = (await db.execute(q.offset((page-1)*limit).limit(limit))).scalars().all()
    items = [{"id":m.id,"user_id":m.user_id,"username":m.user.username,"content":m.content,"time":str(m.created_at)} for m in reversed(messages)]
    return {"total": total, "items": items}
