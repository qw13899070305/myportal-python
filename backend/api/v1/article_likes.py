"""文章点赞 / 收藏接口（可拆卸扩展）。

挂载在 ``/api/v1/articles`` 下：

- ``POST /articles/{id}/like``      点赞 / 取消点赞
- ``POST /articles/{id}/bookmark``  收藏 / 取消收藏

把本文件删掉，文章的读写与评论都不受影响，只是少了点赞收藏能力。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.article_common import can_view
from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.article import Article, Bookmark, Like
from backend.models.user import User
from backend.services.notifications import notify

router = APIRouter()


async def _load_visible(db: AsyncSession, article_id: int, user: User) -> Article:
    """取出文章并确认当前用户可见（点赞/收藏不能作用于看不到的文章）。"""
    from fastapi import HTTPException

    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    if not can_view(article, user):
        raise HTTPException(status_code=403, detail="无权操作该文章")
    return article


@router.post("/{article_id}/like")
async def toggle_like(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """点赞 / 取消点赞。"""
    article = await _load_visible(db, article_id, current_user)

    existing = await db.scalar(
        select(Like).where(Like.article_id == article.id, Like.user_id == current_user.id)
    )
    if existing is not None:
        await db.delete(existing)
        liked = False
    else:
        db.add(Like(article_id=article.id, user_id=current_user.id))
        liked = True
        await notify(
            db,
            user_id=article.author_id,
            from_user_id=current_user.id,
            type="like",
            content=f"{current_user.username} 点赞了你的文章《{article.title}》",
        )

    await db.commit()
    count = (
        await db.scalar(select(func.count()).select_from(Like).where(Like.article_id == article.id))
        or 0
    )
    return {"liked": liked, "likes_count": count}


@router.post("/{article_id}/bookmark")
async def toggle_bookmark(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """收藏 / 取消收藏。"""
    article = await _load_visible(db, article_id, current_user)

    existing = await db.scalar(
        select(Bookmark).where(
            Bookmark.article_id == article.id, Bookmark.user_id == current_user.id
        )
    )
    if existing is not None:
        await db.delete(existing)
        bookmarked = False
    else:
        db.add(Bookmark(article_id=article.id, user_id=current_user.id))
        bookmarked = True

    await db.commit()
    return {"bookmarked": bookmarked}
