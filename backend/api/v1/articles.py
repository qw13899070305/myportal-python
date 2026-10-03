"""文章接口（组装配件）。

本模块只保留**列表查询**，其余都拆成了可以单独摘掉的零件：

===========================  ============================================
模块                          接口
===========================  ============================================
``article_crud.py``          POST /, POST /submit, GET/PATCH/PUT/DELETE /{id}
``article_tags.py``          GET /tags
``article_bookmarks.py``     GET /bookmarks/mine, GET /bookmarks/list
``article_likes.py``         POST /{id}/like, POST /{id}/bookmark
``article_review.py``        POST /review/{id}, POST /{id}/review
``comments.py``              GET/POST /{id}/comments
``withdraw.py``              POST /{id}/withdraw
``article_delete.py``        DELETE /admin/{id}
===========================  ============================================

公共逻辑（摘要 / 可见性 / 互动统计）在 :mod:`backend.api.v1.article_common`。

**挂载顺序很重要**：``/tags`` 与 ``/bookmarks/*`` 必须在
``/{article_id}`` 之前注册，否则固定路径会被当成路径参数。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1._loader import include_optional
from backend.api.v1.article_common import VALID_STATUSES, build_list
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import get_current_user_optional, is_admin
from backend.models.article import STATUS_APPROVED, Article, Tag, article_tags
from backend.models.user import User
from backend.schemas.article import ArticleListOut

router = APIRouter()


@router.get("/", response_model=ArticleListOut)
async def list_articles(
    page: int = Query(1, ge=1),
    size: int = Query(settings.PAGE_SIZE_DEFAULT, ge=1, le=settings.PAGE_SIZE_MAX),
    limit: int | None = Query(default=None, ge=1, le=settings.PAGE_SIZE_MAX),
    search: str = Query("", max_length=100),
    tag: str = Query("", max_length=50),
    status_filter: str | None = Query(None, alias="status"),
    mine: bool = False,
    internal: bool | None = Query(default=None, description="只看内部文章"),
    public: bool | None = Query(default=None, description="只看公开文章"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """文章列表。

    - 未登录 / 普通用户：只能看到「已通过且非内部」的文章，外加自己的文章
    - 管理员：可以看到全部文章，并按状态过滤
    """
    if limit is not None:  # 兼容旧前端的 limit 参数
        size = limit

    admin = current_user is not None and is_admin(current_user)
    conditions = []

    if mine:
        if current_user is None:
            raise HTTPException(status_code=401, detail="请先登录")
        conditions.append(Article.author_id == current_user.id)
    elif not admin:
        visible = and_(Article.status == STATUS_APPROVED, Article.is_internal.is_(False))
        if current_user is not None:
            conditions.append(or_(visible, Article.author_id == current_user.id))
        else:
            conditions.append(visible)

    if internal is True:
        conditions.append(Article.is_internal.is_(True))
    elif public is True:
        conditions.append(Article.is_internal.is_(False))

    if status_filter:
        if status_filter not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="状态参数不合法")
        if not admin:
            raise HTTPException(status_code=403, detail="只有管理员可以按状态过滤")
        conditions.append(Article.status == status_filter)

    stmt = select(Article)
    if tag.strip():
        stmt = stmt.join(article_tags, Article.id == article_tags.c.article_id).join(
            Tag, Tag.id == article_tags.c.tag_id
        )
        conditions.append(Tag.name == tag.strip())

    if search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(or_(Article.title.ilike(pattern), Article.content.ilike(pattern)))

    stmt = stmt.where(*conditions)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    result = await db.execute(
        stmt.order_by(Article.is_pinned.desc(), Article.created_at.desc(), Article.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    articles = result.scalars().unique().all()
    return ArticleListOut(total=total, items=await build_list(db, list(articles), current_user))


# ---------------- 组内的子零件 ----------------
# 顺序：固定路径（tags / bookmarks）必须排在 /{article_id} 之前
PARTS: list[tuple[str, str, list[str]]] = [
    ("backend.api.v1.article_tags", "", ["文章"]),
    ("backend.api.v1.article_bookmarks", "", ["文章"]),
    ("backend.api.v1.article_crud", "", ["文章"]),
]

for _module, _prefix, _tags in PARTS:
    include_optional(router, _module, _prefix, _tags)

__all__ = ["PARTS", "list_articles", "router"]
