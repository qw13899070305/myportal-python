"""文章接口的公共内核。

把「摘要 / 标签解析 / 互动统计 / 可见性判断」抽到这里，
这样列表、详情、点赞收藏、审核、评论、下架、删除这些模块
都可以各自独立摘掉，而不需要互相 import。
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import is_admin
from backend.models.article import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    Article,
    Bookmark,
    Comment,
    Like,
    Tag,
)
from backend.models.user import User
from backend.schemas.article import ArticleDetail, ArticleListItem

#: 合法的文章状态
VALID_STATUSES = {STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED}


def summary(content: str, length: int = 160) -> str:
    """从正文生成列表页摘要。"""
    text = " ".join((content or "").split())
    return text[:length] + ("…" if len(text) > length else "")


async def resolve_tags(db: AsyncSession, names: list[str]) -> list[Tag]:
    """按名称获取标签，不存在则创建。"""
    tags: list[Tag] = []
    for name in names:
        tag = await db.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            await db.flush()
        tags.append(tag)
    return tags


async def engagement(
    db: AsyncSession, article_ids: list[int], user: User | None
) -> tuple[dict[int, int], dict[int, int], set[int], set[int]]:
    """批量获取点赞数、评论数，以及当前用户的点赞/收藏状态。"""
    likes: dict[int, int] = {}
    comments: dict[int, int] = {}
    liked: set[int] = set()
    bookmarked: set[int] = set()
    if not article_ids:
        return likes, comments, liked, bookmarked

    rows = await db.execute(
        select(Like.article_id, func.count())
        .where(Like.article_id.in_(article_ids))
        .group_by(Like.article_id)
    )
    likes = {row[0]: row[1] for row in rows.all()}

    rows = await db.execute(
        select(Comment.article_id, func.count())
        .where(Comment.article_id.in_(article_ids))
        .group_by(Comment.article_id)
    )
    comments = {row[0]: row[1] for row in rows.all()}

    if user is not None:
        rows = await db.execute(
            select(Like.article_id).where(Like.article_id.in_(article_ids), Like.user_id == user.id)
        )
        liked = {row[0] for row in rows.all()}
        rows = await db.execute(
            select(Bookmark.article_id).where(
                Bookmark.article_id.in_(article_ids), Bookmark.user_id == user.id
            )
        )
        bookmarked = {row[0] for row in rows.all()}

    return likes, comments, liked, bookmarked


def to_list_item(
    article: Article,
    likes: dict[int, int],
    comments: dict[int, int],
    liked: set[int],
    bookmarked: set[int],
) -> ArticleListItem:
    """ORM 对象 -> 列表项。"""
    return ArticleListItem(
        id=article.id,
        title=article.title,
        summary=summary(article.content),
        author=article.author,
        author_id=article.author_id,
        status=article.status,
        is_pinned=article.is_pinned,
        is_internal=article.is_internal,
        tags=article.tags,
        created_at=article.created_at,
        likes_count=likes.get(article.id, 0),
        comments_count=comments.get(article.id, 0),
        is_liked=article.id in liked,
        is_bookmarked=article.id in bookmarked,
    )


def to_detail(
    article: Article,
    likes: dict[int, int],
    comments: dict[int, int],
    liked: set[int],
    bookmarked: set[int],
) -> ArticleDetail:
    """ORM 对象 -> 详情（列表项 + 正文）。"""
    return ArticleDetail(
        **to_list_item(article, likes, comments, liked, bookmarked).model_dump(),
        content=article.content,
        updated_at=article.updated_at,
    )


def can_view(article: Article, user: User | None) -> bool:
    """已通过且非内部的文章对所有人可见；其余仅作者与管理员可见。"""
    if article.status == STATUS_APPROVED and not article.is_internal:
        return True
    if user is None:
        return False
    return article.author_id == user.id or is_admin(user)


async def load_article(db: AsyncSession, article_id: int, user: User | None) -> Article:
    """取出文章并校验可见性。"""
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    if not can_view(article, user):
        raise HTTPException(status_code=403, detail="无权查看该文章")
    return article


async def detail_response(db: AsyncSession, article: Article, user: User | None) -> ArticleDetail:
    """组装单篇文章的详情响应。"""
    likes, comments, liked, bookmarked = await engagement(db, [article.id], user)
    return to_detail(article, likes, comments, liked, bookmarked)


async def build_list(
    db: AsyncSession, articles: list[Article], user: User | None
) -> list[ArticleListItem]:
    """批量组装列表项（一次查询拿齐互动数据）。"""
    likes, comments, liked, bookmarked = await engagement(db, [a.id for a in articles], user)
    return [to_list_item(a, likes, comments, liked, bookmarked) for a in articles]


__all__ = [
    "VALID_STATUSES",
    "build_list",
    "can_view",
    "detail_response",
    "engagement",
    "load_article",
    "resolve_tags",
    "summary",
    "to_detail",
    "to_list_item",
]
