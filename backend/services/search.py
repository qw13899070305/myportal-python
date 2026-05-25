from meilisearch_python_sdk import AsyncClient
from backend.core.config import settings
from fastapi import HTTPException
import logging

logger = logging.getLogger("myportal.search")

async def get_search_client() -> AsyncClient:
    return AsyncClient(url=settings.MEILISEARCH_URL, api_key=settings.MEILISEARCH_API_KEY)

async def index_article(article_id: int, title: str, content: str, author: str, tags: list[str]):
    try:
        client = await get_search_client()
        index = client.index("articles")
        await index.add_documents([{"id": article_id, "title": title, "content": content, "author": author, "tags": tags}])
    except Exception as e:
        logger.warning(f"索引文章 {article_id} 失败: {e}")

async def search_articles(query: str, page: int = 1, limit: int = 10) -> dict:
    try:
        client = await get_search_client()
        index = client.index("articles")
        result = await index.search(query, offset=(page - 1) * limit, limit=limit, attributes_to_highlight=["title", "content"])
        return {"total": result.estimated_total_hits, "items": [{"id": h["id"], "title": h.get("title"), "highlight": h.get("_formatted", {})} for h in result.hits]}
    except Exception as e:
        logger.error(f"搜索异常: {e}")
        raise HTTPException(status_code=503, detail="搜索服务暂时不可用，请稍后重试")

async def delete_article_index(article_id: int):
    try:
        client = await get_search_client()
        index = client.index("articles")
        await index.delete_document(str(article_id))
    except Exception as e:
        logger.warning(f"删除文章索引 {article_id} 失败: {e}")
