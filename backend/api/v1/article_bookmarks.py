"""文章收藏夹接口（可拆卸扩展）。

- ``GET /articles/bookmarks/mine``  当前用户收藏的文章
- ``GET /articles/bookmarks/list``  同上（兼容旧前端路径）

**必须挂载在 ``GET /articles/{article_id}`` 之前**。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.article_common import build_list
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.article import Article, Bookmark
from backend.models.user import User
from backend.schemas.article import ArticleListOut

router = APIRouter()


async def _bookmarks(
    page: int,
    size: int,
    limit: int | None,
    db: AsyncSession,
    current_user: User,
) -> ArticleListOut:
    """收藏列表的公共实现（两个路径共用）。"""
    if limit is not None:  # 兼容旧前端的 limit 参数
        size = limit

    base = (
        select(Article)
        .join(Bookmark, Bookmark.article_id == Article.id)
        .where(Bookmark.user_id == current_user.id)
    )
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    result = await db.execute(
        base.order_by(Bookmark.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    articles = result.scalars().unique().all()
    return ArticleListOut(total=total, items=await build_list(db, list(articles), current_user))


@router.get("/bookmarks/mine", response_model=ArticleListOut)
async def my_bookmarks(
    page: int = Query(1, ge=1),
    size: int = Query(settings.PAGE_SIZE_DEFAULT, ge=1, le=settings.PAGE_SIZE_MAX),
    limit: int | None = Query(default=None, ge=1, le=settings.PAGE_SIZE_MAX),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户收藏的文章。"""
    return await _bookmarks(page, size, limit, db, current_user)


@router.get("/bookmarks/list", response_model=ArticleListOut)
async def my_bookmarks_legacy(
    page: int = Query(1, ge=1),
    size: int = Query(settings.PAGE_SIZE_DEFAULT, ge=1, le=settings.PAGE_SIZE_MAX),
    limit: int | None = Query(default=None, ge=1, le=settings.PAGE_SIZE_MAX),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """兼容旧前端 ``GET /articles/bookmarks/list``。"""
    return await _bookmarks(page, size, limit, db, current_user)
