"""文章的增删改查（可拆卸扩展）。

- ``POST   /articles/``           发布（管理员直接通过，普通用户待审核）
- ``POST   /articles/submit``     发布（兼容旧前端路径）
- ``GET    /articles/{id}``       详情
- ``PATCH  /articles/{id}``       编辑（普通用户改动后需重新审核）
- ``PUT    /articles/{id}``       编辑（兼容旧前端）
- ``DELETE /articles/{id}``       删除（作者或管理员）

**必须挂载在 ``/articles/tags``、``/articles/bookmarks/*`` 之后**，
否则 ``/{article_id}`` 会抢先把固定路径吃掉。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.article_common import (
    VALID_STATUSES,
    detail_response,
    load_article,
    resolve_tags,
)
from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.security import (
    get_current_user,
    get_current_user_optional,
    is_admin,
)
from backend.models.article import STATUS_APPROVED, STATUS_PENDING, Article
from backend.models.user import User
from backend.schemas.article import ArticleCreate, ArticleDetail, ArticleUpdate
from backend.schemas.common import Message
from backend.services.audit import safe_log_action
from backend.services.search import delete_article_index, index_article

router = APIRouter()


async def _create_article(
    payload: ArticleCreate,
    db: AsyncSession,
    current_user: User,
    request: Request | None,
) -> Article:
    """创建文章的公共实现（两个路径共用）。"""
    admin = is_admin(current_user)

    new_status = STATUS_APPROVED if admin else STATUS_PENDING
    if admin and payload.status in VALID_STATUSES:
        new_status = payload.status

    article = Article(
        title=payload.title,
        content=payload.content,
        author_id=current_user.id,
        is_internal=payload.is_internal,
        status=new_status,
    )
    article.tags = await resolve_tags(db, payload.tags)
    db.add(article)
    await db.commit()

    await index_article(
        article.id,
        article.title,
        article.content,
        current_user.username,
        [tag.name for tag in article.tags],
    )
    await safe_log_action(
        db,
        action="article_create",
        user_id=current_user.id,
        detail=f"#{article.id} {article.title}",
        request=request,
    )
    logger.info(f"用户 {current_user.username} 发布文章《{article.title}》")
    return article


@router.post("/", response_model=ArticleDetail, status_code=status.HTTP_201_CREATED)
async def create_article(
    request: Request,
    payload: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发布文章。管理员直接通过，普通用户进入待审核状态。"""
    article = await _create_article(payload, db, current_user, request)
    return await detail_response(db, article, current_user)


@router.post("/submit", response_model=ArticleDetail, status_code=status.HTTP_201_CREATED)
async def submit_article(
    request: Request,
    payload: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """兼容旧前端 ``POST /articles/submit``。"""
    article = await _create_article(payload, db, current_user, request)
    return await detail_response(db, article, current_user)


@router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """文章详情（未通过审核的文章仅作者与管理员可见）。"""
    article = await load_article(db, article_id, current_user)
    return await detail_response(db, article, current_user)


@router.patch("/{article_id}", response_model=ArticleDetail)
async def update_article(
    article_id: int,
    request: Request,
    payload: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑文章：作者或管理员。普通用户改动后需要重新审核。"""
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")

    admin = is_admin(current_user)
    if article.author_id != current_user.id and not admin:
        raise HTTPException(status_code=403, detail="无权修改该文章")

    for field, value in payload.model_dump(exclude_unset=True, exclude={"tags"}).items():
        if field in {"is_pinned", "status"} and not admin:
            continue  # 只有管理员可以置顶 / 直接改状态
        if field == "status" and value not in VALID_STATUSES:
            continue
        setattr(article, field, value)

    if payload.tags is not None:
        article.tags = await resolve_tags(db, payload.tags)

    # 普通用户修改内容后需要重新审核
    if not admin and (payload.title is not None or payload.content is not None):
        article.status = STATUS_PENDING

    db.add(article)
    await db.commit()

    await index_article(
        article.id,
        article.title,
        article.content,
        article.author.username if article.author else "",
        [tag.name for tag in article.tags],
    )
    return await detail_response(db, article, current_user)


@router.put("/{article_id}", response_model=ArticleDetail)
async def update_article_legacy(
    article_id: int,
    request: Request,
    payload: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """兼容旧前端的 PUT 更新。"""
    return await update_article(article_id, request, payload, db=db, current_user=current_user)


@router.delete("/{article_id}", response_model=Message)
async def delete_article(
    article_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除文章：作者或管理员。"""
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.author_id != current_user.id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="无权删除该文章")

    title = article.title
    await db.delete(article)
    await db.commit()
    await delete_article_index(article_id)
    await safe_log_action(
        db,
        action="article_delete",
        user_id=current_user.id,
        detail=f"#{article_id} {title}",
        request=request,
    )
    logger.info(f"用户 {current_user.username} 删除文章 #{article_id}")
    return Message(message="文章已删除")
