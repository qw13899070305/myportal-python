from fastapi import APIRouter, Depends, HTTPException
from backend.core.auth import get_current_user
from backend.services.search import search_articles

router = APIRouter(prefix="/search", tags=["搜索"])

@router.get("/")
async def search(query: str = "", page: int = 1, limit: int = 10, user=Depends(get_current_user)):
    if not query.strip():
        return {"total": 0, "items": []}
    return await search_articles(query, page, limit)
