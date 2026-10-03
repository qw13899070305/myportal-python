"""文章评论接口。"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user, get_current_user_optional, is_admin
from backend.models.article import Comment
from backend.models.user import User
from backend.schemas.article import CommentCreate, CommentListOut, CommentOut
from backend.schemas.common import Message
from backend.services.audit import safe_log_action
from backend.services.notifications import notify

router = APIRouter()


async def _load(db: AsyncSession, article_id: int):
    """取出文章，不存在则 404。"""
    from backend.models.article import Article

    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    return article


def _can_view(article, user):
    """转发到公共内核，避免和 articles.py 互相 import。"""
    from backend.api.v1.article_common import can_view

    return can_view(article, user)


@router.get("/{article_id}/comments", response_model=CommentListOut)
async def get_comments(
    article_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """文章评论列表（按时间正序）。"""
    article = await _load(db, article_id)
    if not _can_view(article, current_user):
        raise HTTPException(status_code=403, detail="无权查看该文章的评论")

    base = select(Comment).where(Comment.article_id == article_id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    result = await db.execute(
        base.order_by(Comment.created_at.asc(), Comment.id.asc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return CommentListOut(total=total, items=result.scalars().all())


@router.post(
    "/{article_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    article_id: int,
    request: Request,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发表评论，并通知文章作者。"""
    article = await _load(db, article_id)
    if not _can_view(article, current_user):
        raise HTTPException(status_code=403, detail="无权评论该文章")

    if payload.parent_id is not None:
        parent = await db.get(Comment, payload.parent_id)
        if parent is None or parent.article_id != article.id:
            raise HTTPException(status_code=400, detail="被回复的评论不存在")

    comment = Comment(
        article_id=article.id,
        user_id=current_user.id,
        parent_id=payload.parent_id,
        content=payload.content,
    )
    db.add(comment)

    await notify(
        db,
        user_id=article.author_id,
        from_user_id=current_user.id,
        type="comment",
        content=f"{current_user.username} 评论了你的文章《{article.title}》",
    )
    if payload.parent_id is not None:
        parent = await db.get(Comment, payload.parent_id)
        if parent is not None and parent.user_id != current_user.id:
            await notify(
                db,
                user_id=parent.user_id,
                from_user_id=current_user.id,
                type="reply",
                content=f"{current_user.username} 回复了你的评论",
            )

    await db.commit()
    await safe_log_action(
        db,
        action="comment_create",
        user_id=current_user.id,
        detail=f"文章 #{article.id}",
        request=request,
    )
    return comment


@router.delete("/{article_id}/comments/{comment_id}", response_model=Message)
async def delete_comment(
    article_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除评论：评论作者、文章作者或管理员。"""
    comment = await db.get(Comment, comment_id)
    if comment is None or comment.article_id != article_id:
        raise HTTPException(status_code=404, detail="评论不存在")

    article = await _load(db, article_id)
    if (
        comment.user_id != current_user.id
        and article.author_id != current_user.id
        and not is_admin(current_user)
    ):
        raise HTTPException(status_code=403, detail="无权删除该评论")

    await db.delete(comment)
    await db.commit()
    return Message(message="评论已删除")
