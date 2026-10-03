"""搜索扩展包。

后端按 ``priority`` 从高到低挑选：

===============  ==========  ==========================================
模块             优先级      说明
===============  ==========  ==========================================
``meilisearch``  100         配置了 ``MEILISEARCH_URL`` 时启用
``database``     0           永远可用的兜底（SQL LIKE）
===============  ==========  ==========================================

删掉 ``meilisearch.py`` 就只剩数据库搜索，功能不中断；
再加一个 ``elasticsearch.py`` 之类的文件即可自动接入。
"""

from __future__ import annotations

from backend.core.logger import logger
from backend.extensions.registry import discover_extensions
from backend.extensions.search.base import SearchBackend, SearchHit, SearchResult

registry = discover_extensions(__name__, "search", "搜索后端", skip={"base"})


def backends() -> list[SearchBackend]:
    """按优先级从高到低返回所有已注册后端。"""
    return registry.sorted_items(key=lambda item: -getattr(item, "priority", 0))


def active_backend() -> SearchBackend | None:
    """返回当前可用的最高优先级后端。"""
    for backend in backends():
        try:
            if backend.available():
                return backend
        except Exception as exc:  # pragma: no cover - 后端自身实现有误
            logger.warning(f"搜索后端 {backend!r} 可用性检查失败: {exc}")
    return None


async def search(query: str, page: int = 1, limit: int = 10) -> SearchResult:
    """用当前后端搜索；失败时依次降级到后面的后端。"""
    query = (query or "").strip()
    if not query:
        return SearchResult(total=0, items=[], engine="none")

    for backend in backends():
        try:
            if not backend.available():
                continue
            return await backend.search(query, page, limit)
        except Exception as exc:
            logger.warning(f"搜索后端 {backend!r} 失败，尝试下一个: {exc}")
    return SearchResult(total=0, items=[], engine="none")


async def index_article(
    article_id: int, title: str, content: str, author: str, tags: list[str]
) -> None:
    """把文章写进所有可用后端的索引（失败只记日志）。"""
    for backend in backends():
        try:
            if backend.available():
                await backend.index_article(article_id, title, content, author, tags)
        except Exception as exc:
            logger.warning(f"索引文章 {article_id} 到 {backend!r} 失败: {exc}")


async def delete_article(article_id: int) -> None:
    """从所有可用后端的索引里删除文章。"""
    for backend in backends():
        try:
            if backend.available():
                await backend.delete_article(article_id)
        except Exception as exc:
            logger.warning(f"从 {backend!r} 删除文章 {article_id} 索引失败: {exc}")


async def close_all() -> None:
    """关闭所有后端的连接。"""
    for backend in backends():
        try:
            await backend.close()
        except Exception:  # pragma: no cover - 关闭失败不影响退出
            pass


__all__ = [
    "SearchBackend",
    "SearchHit",
    "SearchResult",
    "active_backend",
    "backends",
    "close_all",
    "delete_article",
    "index_article",
    "registry",
    "search",
]
