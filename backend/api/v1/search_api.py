"""全文搜索接口。

MeiliSearch 可用时走 MeiliSearch，否则自动降级为数据库模糊查询
（见 :mod:`backend.services.search`）。
"""

from fastapi import APIRouter, Depends, Query

from backend.core.security import get_current_user
from backend.models.user import User
from backend.services.search import search_articles

router = APIRouter()


@router.get("/")
async def search(
    query: str = Query("", max_length=200),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    """搜索文章（需要登录）。"""
    if not query.strip():
        return {"total": 0, "items": [], "engine": "none"}
    return await search_articles(query, page, limit)
