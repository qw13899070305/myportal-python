"""MeiliSearch 搜索后端（可选增强）。

只有配置了 ``MEILISEARCH_URL`` 才会被选中；调用失败时抛异常，
由外层 ``services/search.py`` 自动回退到数据库后端。
"""

from __future__ import annotations

from backend.core.config import settings
from backend.core.logger import logger
from backend.extensions.registry import get_registry
from backend.extensions.search.base import SearchBackend, SearchHit, SearchResult

INDEX_NAME = "articles"


class MeiliSearchBackend(SearchBackend):
    name = "meilisearch"
    #: 比数据库后端高，配置了就优先用它
    priority = 100

    def __init__(self) -> None:
        self._client = None

    # ---------------- 连接 ----------------

    def available(self) -> bool:
        return bool(settings.MEILISEARCH_URL.strip())

    async def _get_client(self):
        if not self.available():
            return None
        if self._client is None:
            try:
                from meilisearch_python_sdk import AsyncClient
            except ImportError:  # pragma: no cover - 没装 SDK 时静默降级
                logger.warning("未安装 meilisearch-python-sdk，搜索降级为数据库查询")
                return None
            self._client = AsyncClient(
                url=settings.MEILISEARCH_URL,
                api_key=settings.MEILISEARCH_API_KEY or None,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:  # pragma: no cover - 关闭失败不影响退出
                pass
            self._client = None

    # ---------------- 搜索 ----------------

    async def search(self, query: str, page: int = 1, limit: int = 10) -> SearchResult:
        client = await self._get_client()
        if client is None:
            raise RuntimeError("MeiliSearch 不可用")

        index = client.index(INDEX_NAME)
        result = await index.search(
            query,
            offset=(page - 1) * limit,
            limit=limit,
            attributes_to_highlight=["title", "content"],
        )
        return SearchResult(
            total=getattr(result, "estimated_total_hits", None) or len(result.hits),
            items=[
                SearchHit(
                    id=hit.get("id"),
                    title=hit.get("title") or "",
                    highlight=hit.get("_formatted", {}),
                    content_snippet=(hit.get("content") or "")[:200],
                )
                for hit in result.hits
            ],
            engine=self.name,
        )

    # ---------------- 索引 ----------------

    async def index_article(
        self, article_id: int, title: str, content: str, author: str, tags: list[str]
    ) -> None:
        client = await self._get_client()
        if client is None:
            return
        await client.index(INDEX_NAME).add_documents(
            [
                {
                    "id": article_id,
                    "title": title,
                    "content": content,
                    "author": author,
                    "tags": tags,
                }
            ]
        )

    async def delete_article(self, article_id: int) -> None:
        client = await self._get_client()
        if client is None:
            return
        await client.index(INDEX_NAME).delete_document(str(article_id))


get_registry("search").register(MeiliSearchBackend())
