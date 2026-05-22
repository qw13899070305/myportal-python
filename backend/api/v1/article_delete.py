from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import get_db
from backend.core.auth import get_current_user, RoleChecker
from backend.models.article import Article

router = APIRouter(prefix="/articles", tags=["删除"])

@router.delete("/admin/{article_id}")
async def admin_delete_article(article_id: int, user=Depends(RoleChecker(["admin","super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "文章不存在")
    await db.delete(article)
    await db.commit()
    return {"msg": "文章已删除"}
