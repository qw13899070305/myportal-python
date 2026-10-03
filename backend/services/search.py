"""文章搜索（对外门面）。

真正的实现拆成了**可插拔的搜索后端**，放在
:mod:`backend.extensions.search` 里：

    backend/extensions/search/database.py      永远可用的兜底（SQL LIKE）
    backend/extensions/search/meilisearch.py   配置 MEILISEARCH_URL 后启用

挑选规则：按 ``priority`` 从高到低取第一个 ``available()`` 为真的后端；
某个后端调用失败会自动降级到后面的后端，所以**搜索永远不会因为
外部服务挂掉而不可用**。

本模块保留了原有的函数名，历史代码与测试无需改动。
"""

from __future__ import annotations

from backend.core.logger import logger
from backend.extensions.search import (  # noqa: F401
    SearchBackend,
    SearchHit,
    SearchResult,
    active_backend,
    backends,
)
from backend.extensions.search import close_all as _close_all
from backend.extensions.search import delete_article as _delete_article
from backend.extensions.search import index_article as _index_article
from backend.extensions.search import search as _search


async def search_articles(query: str, page: int = 1, limit: int = 10) -> dict:
    """搜索文章，返回 ``{total, items, engine}``。"""
    result = await _search(query, page, limit)
    return result.to_dict()


async def index_article(
    article_id: int,
    title: str,
    content: str,
    author: str = "",
    tags: list[str] | None = None,
) -> None:
    """把文章写进搜索索引（失败只记日志，不影响主流程）。"""
    await _index_article(article_id, title, content, author, tags or [])


async def delete_article_index(article_id: int) -> None:
    """从搜索索引里删除文章。"""
    await _delete_article(article_id)


def get_search_client() -> SearchBackend | None:
    """返回当前生效的搜索后端（供健康检查展示）。"""
    return active_backend()


def search_engine_name() -> str:
    """当前搜索引擎的名字，例如 ``meilisearch`` / ``database``。"""
    backend = active_backend()
    return backend.name if backend else "none"


async def close_search_client() -> None:
    """关闭所有搜索后端的连接。"""
    await _close_all()
    logger.debug("搜索后端已全部关闭")


__all__ = [
    "SearchBackend",
    "SearchHit",
    "SearchResult",
    "active_backend",
    "backends",
    "close_search_client",
    "delete_article_index",
    "get_search_client",
    "index_article",
    "search_articles",
    "search_engine_name",
]
