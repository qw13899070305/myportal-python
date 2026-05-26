from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from backend.core.database import get_db
from backend.core.auth.dependencies import get_current_user
from backend.models.user import User
from backend.models.article import Article, Bookmark
from backend.schemas.article import ArticleCreate, ArticleOut, ArticleList

router = APIRouter()


@router.get("/", response_model=ArticleList)
async def list_articles(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tag: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    q = select(Article).order_by(Article.created_at.desc())
    count_q = select(func.count(Article.id)).select_from(Article)

    if tag:
        q = q.where(Article.tags.contains([tag]))
        count_q = count_q.where(Article.tags.contains([tag]))
    if search:
        q = q.where(Article.title.contains(search) | Article.content.contains(search))
        count_q = count_q.where(Article.title.contains(search) | Article.content.contains(search))

    total = await db.scalar(count_q)
    q = q.offset((page - 1) * size).limit(size)
    result = await db.execute(q)
    articles = result.scalars().all()

    user_bookmarks = set()
    if current_user:
        bm_result = await db.execute(
            select(Bookmark.article_id).where(Bookmark.user_id == current_user.id)
        )
        user_bookmarks = {row[0] for row in bm_result.all()}

    items = []
    for a in articles:
        items.append({
            "id": a.id,
            "title": a.title,
            "summary": a.summary if hasattr(a, 'summary') else a.content[:200],
            "tags": [t.name for t in a.tags] if a.tags else [],
            "author": a.author.username if a.author else "未知",
            "created_at": a.created_at.isoformat(),
            "is_bookmarked": a.id in user_bookmarks
        })

    return {"total": total, "items": items}


@router.post("/", response_model=ArticleOut, status_code=201)
async def create_article(
    article_data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    article = Article(**article_data.model_dump(), author_id=current_user.id)
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


@router.delete("/{article_id}")
async def delete_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 权限检查：只有作者或管理员可以删除
    is_admin = any(role.name == "admin" for role in current_user.roles)
    if article.author_id != current_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="无权删除此文章")

    await db.delete(article)
    await db.commit()
    return {"message": "文章已删除"}