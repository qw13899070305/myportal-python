"""文章删除（管理员专用路径）。

保留独立的 ``DELETE /articles/admin/{article_id}``，
与 ``DELETE /articles/{article_id}`` 的区别是：
只允许管理员调用，且会连带清理搜索索引。
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.security import RoleChecker
from backend.models.article import Article
from backend.models.user import User
from backend.services.audit import safe_log_action
from backend.services.search import delete_article_index

router = APIRouter()

admin_only = RoleChecker(["admin", "super_admin"])


@router.delete("/admin/{article_id}")
async def admin_delete_article(
    article_id: int,
    request: Request,
    user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    """管理员强制删除文章。"""
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")

    title = article.title
    await db.delete(article)
    await db.commit()
    await delete_article_index(article_id)
    await safe_log_action(
        db,
        action="article_admin_delete",
        user_id=user.id,
        detail=f"#{article_id} {title}",
        request=request,
    )
    logger.info(f"管理员 {user.username} 删除文章 #{article_id}")
    return {"msg": "文章已删除", "message": "文章已删除"}
