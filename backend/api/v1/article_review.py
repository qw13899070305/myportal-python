"""文章审核接口（可拆卸扩展）。

挂载在 ``/api/v1/articles`` 下，提供两种调用方式：

- ``POST /articles/review/{id}?action=approve|reject``   兼容旧前端
- ``POST /articles/{id}/review``  body ``{"action": "..."}``

把本文件删掉，文章依然可以正常投稿与阅读，只是没有审核入口
（管理员仍可通过 ``PATCH /articles/{id}`` 改状态）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.article_common import (
    VALID_STATUSES,
    detail_response,
)
from backend.core.database import get_db
from backend.core.security import get_current_user, is_admin
from backend.models.article import STATUS_APPROVED, STATUS_REJECTED, Article
from backend.models.user import User
from backend.schemas.article import ArticleDetail, ArticleReview
from backend.services.audit import safe_log_action
from backend.services.notifications import notify
from backend.services.search import index_article

router = APIRouter()


async def _review(
    article_id: int,
    payload: ArticleReview,
    db: AsyncSession,
    current_user: User,
    request: Request | None = None,
) -> ArticleDetail:
    """审核核心逻辑（两种入口共用）。"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="权限不足")

    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")

    approved = payload.action == "approve"
    article.status = STATUS_APPROVED if approved else STATUS_REJECTED
    db.add(article)

    await notify(
        db,
        user_id=article.author_id,
        from_user_id=current_user.id,
        type="article_review",
        content=f"你的文章《{article.title}》已{'通过审核' if approved else '被拒绝'}",
    )
    await db.commit()

    await safe_log_action(
        db,
        action="article_review",
        user_id=current_user.id,
        detail=f"#{article.id} {article.title} -> {article.status}",
        request=request,
    )

    if approved:
        await index_article(
            article.id,
            article.title,
            article.content,
            article.author.username if article.author else "",
            [tag.name for tag in article.tags],
        )
    return await detail_response(db, article, current_user)


@router.post("/review/{article_id}", response_model=ArticleDetail)
async def review_article_by_path(
    article_id: int,
    request: Request,
    action: str = Query(..., pattern="^(approve|reject)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """审核文章（兼容旧前端 ``POST /articles/review/{id}?action=``）。"""
    if action not in {"approve", "reject"}:  # pragma: no cover - 由 Query 正则兜住
        raise HTTPException(status_code=400, detail="状态参数不合法")
    return await _review(article_id, ArticleReview(action=action), db, current_user, request)


@router.post("/{article_id}/review", response_model=ArticleDetail)
async def review_article(
    article_id: int,
    request: Request,
    payload: ArticleReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """审核文章（仅管理员），body: ``{"action": "approve"|"reject"}``。"""
    if payload.action not in VALID_STATUSES | {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="状态参数不合法")
    return await _review(article_id, payload, db, current_user, request)
