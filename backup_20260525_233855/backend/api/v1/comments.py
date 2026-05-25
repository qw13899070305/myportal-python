from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.article import Comment

router = APIRouter(prefix="/articles", tags=["评论"])

@router.get("/{article_id}/comments")
async def get_comments(article_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(
        select(Comment).where(Comment.article_id == article_id).order_by(Comment.created_at.asc())
    )
    comments = result.scalars().all()
    items = [{"id": c.id, "content": c.content, "created_at": c.created_at, "user": {"username": c.user.username}} for c in comments]
    return {"items": items}
