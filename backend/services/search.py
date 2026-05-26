from meilisearch_python_sdk import AsyncClient
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.models.article import Article
from sqlalchemy import select, func
from fastapi import HTTPException
import logging

logger = logging.getLogger("myportal.search")

_client = None


async def get_search_client() -> AsyncClient:
    global _client
    if _client is None and settings.MEILISEARCH_URL:
        _client = AsyncClient(
            url=settings.MEILISEARCH_URL,
            api_key=settings.MEILISEARCH_API_KEY
        )
    return _client


async def index_article(article_id: int, title: str, content: str, author: str, tags: list[str]):
    try:
        client = await get_search_client()
        if client:
            index = client.index("articles")
            await index.add_documents([
                {
                    "id": article_id,
                    "title": title,
                    "content": content,
                    "author": author,
                    "tags": tags
                }
            ])
    except Exception as e:
        logger.warning(f"索引文章 {article_id} 失败: {e}")


async def search_articles(query: str, page: int = 1, limit: int = 10) -> dict:
    # 优先使用 MeiliSearch
    client = await get_search_client()
    if client:
        try:
            index = client.index("articles")
            result = await index.search(
                query,
                offset=(page - 1) * limit,
                limit=limit,
                attributes_to_highlight=["title", "content"]
            )
            return {
                "total": result.estimated_total_hits,
                "items": [
                    {
                        "id": h["id"],
                        "title": h.get("title"),
                        "highlight": h.get("_formatted", {})
                    }
                    for h in result.hits
                ]
            }
        except Exception as e:
            logger.warning(f"MeiliSearch 搜索失败，回退到数据库搜索: {e}")

    # 降级为数据库模糊查询
    async with AsyncSessionLocal() as db:
        count_q = select(func.count(Article.id)).where(
            Article.title.contains(query) | Article.content.contains(query)
        )
        total = await db.scalar(count_q)
        q = select(Article).where(
            Article.title.contains(query) | Article.content.contains(query)
        ).order_by(Article.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await db.execute(q)
        articles = result.scalars().all()
        items = []
        for a in articles:
            items.append({
                "id": a.id,
                "title": a.title,
                "highlight": {},
                "content_snippet": a.content[:200]
            })
        return {"total": total, "items": items}


async def delete_article_index(article_id: int):
    try:
        client = await get_search_client()
        if client:
            index = client.index("articles")
            await index.delete_document(str(article_id))
    except Exception as e:
        logger.warning(f"删除文章索引 {article_id} 失败: {e}")