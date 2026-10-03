"""文章下架（撤回）接口。"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user, is_admin
from backend.models.article import STATUS_APPROVED, STATUS_PENDING, Article
from backend.models.user import User
from backend.services.audit import safe_log_action
from backend.services.search import delete_article_index

router = APIRouter()


@router.post("/{article_id}/withdraw")
async def withdraw_article(
    article_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """下架文章：作者或管理员。下架后回到「待审核」，需要重新审核才能发布。"""
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.author_id != user.id and not is_admin(user):
        raise HTTPException(status_code=403, detail="无权操作该文章")
    if article.status != STATUS_APPROVED:
        raise HTTPException(status_code=400, detail="只有已发布的文章可以下架")

    article.status = STATUS_PENDING
    db.add(article)
    await db.commit()
    await delete_article_index(article.id)
    await safe_log_action(
        db,
        action="article_withdraw",
        user_id=user.id,
        detail=f"#{article.id} {article.title}",
        request=request,
    )
    return {"msg": "文章已下架，等待重新审核", "message": "文章已下架，等待重新审核"}
