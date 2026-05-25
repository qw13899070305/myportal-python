from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.article import Article
from backend.models.user import User

router = APIRouter(prefix="/articles", tags=["撤回"])

@router.post("/{article_id}/withdraw")
async def withdraw_article(article_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "文章不存在")
    if article.author_id != user.id and not any(r.name in ["admin","super_admin"] for r in user.roles):
        raise HTTPException(403, "无权操作")
    if article.status != "approved":
        raise HTTPException(400, "文章当前状态不可撤回")
    article.status = "rejected"
    await db.commit()
    return {"msg": "文章已下架"}
