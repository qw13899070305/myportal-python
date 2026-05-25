from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.chat import ChatMessage

router = APIRouter(prefix="/chat", tags=["聊天"])

@router.get("/messages")
async def get_history(page: int = Query(1, ge=1), page_size: int = Query(30, le=100),
                      db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    stmt = select(ChatMessage).where(ChatMessage.is_recalled == False)\
           .order_by(desc(ChatMessage.created_at)).offset((page-1)*page_size).limit(page_size)
    result = await db.execute(stmt)
    messages = list(reversed(result.scalars().all()))
    return [{
        "id": m.id,
        "user_id": m.user_id,
        "username": m.user.username if m.user else "未知",
        "content": m.content,
        "time": str(m.created_at),
        "is_recalled": m.is_recalled
    } for m in messages]
