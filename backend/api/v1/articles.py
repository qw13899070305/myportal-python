from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from backend.core.database import get_db
from backend.core.auth import get_current_user, RoleChecker
from backend.core.utils import sanitize_html_bleach
from backend.models.article import Article, Comment, Like, Tag, Bookmark
from backend.models.chat import Notification
from pydantic import BaseModel

router = APIRouter(prefix="/articles", tags=["文章"])

class ArticleCreate(BaseModel):
    title: str
    content: str
    tags: list[str] = []
    is_internal: bool = False

@router.get("/")
async def list_articles(page: int=1, limit: int=10, status: str="approved", tag: str=None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    is_admin = any(r.name in ["admin","super_admin","moderator","author"] for r in user.roles)
    conditions = [Article.status == status]
    if not is_admin:
        conditions.append(Article.is_internal == False)
    q = select(Article).where(and_(*conditions)).order_by(Article.is_pinned.desc(), Article.created_at.desc())
    if tag:
        q = q.where(Article.tags.any(Tag.name == tag))
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    articles = (await db.execute(q.offset((page-1)*limit).limit(limit))).scalars().all()
    items = []
    for a in articles:
        is_bookmarked = False
        if user:
            bm = await db.execute(select(Bookmark).where(Bookmark.article_id==a.id, Bookmark.user_id==user.id))
            is_bookmarked = bm.scalar_one_or_none() is not None
        items.append({
            "id":a.id,"title":a.title,"author":a.author.username,"status":a.status,
            "is_pinned":a.is_pinned,"is_internal":a.is_internal,"created_at":a.created_at,
            "tags":[t.name for t in a.tags],"likes_count":len(a.likes),"comments_count":len(a.comments),
            "is_bookmarked":is_bookmarked
        })
    return {"total":total,"items":items}

@router.get("/internal")
async def list_internal_articles(page: int=1, limit: int=10, user=Depends(RoleChecker(["admin","super_admin","moderator","author"])), db: AsyncSession = Depends(get_db)):
    q = select(Article).where(Article.is_internal==True, Article.status=="approved").order_by(Article.created_at.desc())
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    articles = (await db.execute(q.offset((page-1)*limit).limit(limit))).scalars().all()
    items = []
    for a in articles:
        items.append({
            "id":a.id,"title":a.title,"author":a.author.username,"created_at":a.created_at
        })
    return {"total":total,"items":items}

@router.get("/{article_id}")
async def get_article(article_id: int, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.id == article_id, Article.status == "approved"))
    a = result.scalar_one_or_none()
    if not a: raise HTTPException(404, "文章不存在")
    if a.is_internal and not any(r.name in ["admin","super_admin","moderator","author"] for r in user.roles):
        raise HTTPException(403, "无权查看内部文章")
    is_liked = False; is_bookmarked = False
    like_res = await db.execute(select(Like).where(Like.article_id==a.id, Like.user_id==user.id))
    is_liked = like_res.scalar_one_or_none() is not None
    bm_res = await db.execute(select(Bookmark).where(Bookmark.article_id==a.id, Bookmark.user_id==user.id))
    is_bookmarked = bm_res.scalar_one_or_none() is not None
    return {
        "id":a.id,"title":a.title,"content":a.content,"author":a.author.username,
        "status":a.status,"is_pinned":a.is_pinned,"is_internal":a.is_internal,
        "created_at":a.created_at,"tags":[t.name for t in a.tags],
        "likes_count":len(a.likes),"comments_count":len(a.comments),
        "is_liked":is_liked,"is_bookmarked":is_bookmarked
    }

@router.post("/submit")
async def submit(data: ArticleCreate, user=Depends(RoleChecker(["author","admin","super_admin"])), db: AsyncSession = Depends(get_db)):
    if any(r.name in ["admin","super_admin"] for r in user.roles):
        status = "approved"
    else:
        status = "pending"
    article = Article(title=sanitize_html_bleach(data.title), content=data.content, author_id=user.id, status=status, is_internal=data.is_internal)
    for tname in data.tags:
        tag_res = await db.execute(select(Tag).where(Tag.name == tname))
        tag = tag_res.scalar_one_or_none()
        if not tag:
            tag = Tag(name=tname); db.add(tag)
        article.tags.append(tag)
    db.add(article)
    await db.commit()
    return {"msg":"投稿成功，等待审核"}

@router.post("/review/{article_id}")
async def review(article_id: int, action: str, _=Depends(RoleChecker(["moderator","admin","super_admin"])), db: AsyncSession = Depends(get_db)):
    if action not in ("approve","reject"): raise HTTPException(400)
    result = await db.execute(select(Article).where(Article.id == article_id))
    a = result.scalar_one_or_none()
    if not a: raise HTTPException(404)
    a.status = "approved" if action == "approve" else "rejected"
    await db.commit()
    return {"msg":"操作成功"}

@router.post("/{article_id}/like")
async def toggle_like(article_id: int, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    like_res = await db.execute(select(Like).where(Like.article_id==article_id, Like.user_id==user.id))
    like = like_res.scalar_one_or_none()
    if like:
        await db.delete(like); msg = "取消点赞"
    else:
        like = Like(article_id=article_id, user_id=user.id); db.add(like)
        # 发送通知
        article = await db.get(Article, article_id)
        if article and article.author_id != user.id:
            notif = Notification(user_id=article.author_id, from_user_id=user.id, type="like", content=f"{user.username} 赞了你的文章《{article.title}》")
            db.add(notif)
        msg = "点赞成功"
    await db.commit()
    return {"msg":msg}

@router.post("/{article_id}/bookmark")
async def toggle_bookmark(article_id: int, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    bm_res = await db.execute(select(Bookmark).where(Bookmark.article_id==article_id, Bookmark.user_id==user.id))
    bm = bm_res.scalar_one_or_none()
    if bm:
        await db.delete(bm); msg = "取消收藏"
    else:
        bm = Bookmark(article_id=article_id, user_id=user.id); db.add(bm); msg = "收藏成功"
    await db.commit()
    return {"msg":msg}

@router.get("/bookmarks/list")
async def list_bookmarks(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bookmark).where(Bookmark.user_id==user.id).order_by(Bookmark.created_at.desc()))
    bookmarks = result.scalars().all()
    items = []
    for bm in bookmarks:
        article = await db.get(Article, bm.article_id)
        if article:
            items.append({"id":article.id,"title":article.title,"created_at":article.created_at})
    return {"items":items}

@router.post("/{article_id}/comment")
async def comment(article_id: int, content: str, parent_id: int|None=None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    c = Comment(article_id=article_id, user_id=user.id, content=sanitize_html_bleach(content), parent_id=parent_id)
    db.add(c)
    article = await db.get(Article, article_id)
    if article and article.author_id != user.id:
        notif = Notification(user_id=article.author_id, from_user_id=user.id, type="comment", content=f"{user.username} 评论了你的文章《{article.title}》")
        db.add(notif)
    await db.commit()
    return {"msg":"评论成功"}

@router.post("/{article_id}/sticky")
async def toggle_sticky(article_id: int, _=Depends(RoleChecker(["admin","super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.id == article_id))
    a = result.scalar_one_or_none()
    if a: a.is_pinned = not a.is_pinned; await db.commit()
    return {"msg":"操作成功"}
