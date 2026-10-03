"""数据库搜索后端（永远可用的兜底）。

用 SQL ``ILIKE`` 做模糊匹配，不需要任何外部服务。
性能不如 MeiliSearch，但保证「搜索」这个功能在任何部署形态下都可用。
"""

from __future__ import annotations

from sqlalchemy import func, or_, select

from backend.core.database import AsyncSessionLocal
from backend.extensions.registry import get_registry
from backend.extensions.search.base import SearchBackend, SearchHit, SearchResult
from backend.models.article import Article


class DatabaseSearchBackend(SearchBackend):
    name = "database"
    #: 最低优先级：只有没有更好的后端时才会被选中
    priority = 0

    #: 单条摘要长度
    snippet_length = 200

    def available(self) -> bool:
        return True

    async def search(self, query: str, page: int = 1, limit: int = 10) -> SearchResult:
        query = (query or "").strip()
        if not query:
            return SearchResult(total=0, items=[], engine=self.name)

        pattern = f"%{query}%"
        condition = or_(Article.title.ilike(pattern), Article.content.ilike(pattern))

        async with AsyncSessionLocal() as db:
            total = await db.scalar(select(func.count()).select_from(Article).where(condition)) or 0
            result = await db.execute(
                select(Article)
                .where(condition)
                .order_by(Article.created_at.desc(), Article.id.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
            items = [
                SearchHit(
                    id=article.id,
                    title=article.title,
                    highlight={},
                    content_snippet=(article.content or "")[: self.snippet_length],
                )
                for article in result.scalars().all()
            ]

        return SearchResult(total=total, items=items, engine=self.name)


get_registry("search").register(DatabaseSearchBackend())
