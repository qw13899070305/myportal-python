from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.article import Article  # 假设存在

router = APIRouter()

@router.get("/")
async def list_articles(db: AsyncSession = Depends(get_db), page: int = 1, size: int = 20):
    # 示例实现，可根据需要完善
    result = await db.execute(select(Article).offset((page-1)*size).limit(size))
    articles = result.scalars().all()
    return {"code": 200, "data": articles}

@router.post("/")
async def create_article(data: dict, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    article = Article(**data, author_id=current_user.id)
    db.add(article)
    await db.commit()
    return {"code": 200, "message": "创建成功", "data": {"id": article.id}}