"""搜索后端的基类与数据模型。

一个搜索后端 = 一个模块 + 一个 :class:`SearchBackend` 子类。
注册表按 ``priority`` 从高到低挑第一个 ``available()`` 为真的后端，
所以「数据库 LIKE」是永远可用的兜底，MeiliSearch 是可选增强。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SearchHit:
    """一条搜索结果。"""

    id: int
    title: str
    highlight: dict = field(default_factory=dict)
    content_snippet: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "highlight": self.highlight,
            "content_snippet": self.content_snippet,
        }


@dataclass
class SearchResult:
    """一次搜索的结果集。"""

    total: int
    items: list[SearchHit]
    engine: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "items": [hit.to_dict() for hit in self.items],
            "engine": self.engine,
        }


class SearchBackend(ABC):
    """搜索后端接口。

    只要求实现 :meth:`search`；索引相关的三个方法默认是空操作，
    这样"只读后端"（例如纯数据库查询）不用写无意义的桩代码。
    """

    #: 后端名称
    name: str = ""
    #: 越大越优先被选中
    priority: int = 0

    @abstractmethod
    def available(self) -> bool:
        """当前配置下这个后端能不能用。"""

    @abstractmethod
    async def search(self, query: str, page: int = 1, limit: int = 10) -> SearchResult:
        """执行搜索。"""

    async def index_article(  # noqa: B027 - 可选的钩子，不是必须实现的抽象方法
        self, article_id: int, title: str, content: str, author: str, tags: list[str]
    ) -> None:
        """写入/更新索引（不需要索引的后端可以不实现）。"""

    async def delete_article(self, article_id: int) -> None:  # noqa: B027 - 可选钩子
        """从索引里删除文章。"""

    async def close(self) -> None:  # noqa: B027 - 可选钩子
        """释放连接。"""

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"<{type(self).__name__} {self.name} priority={self.priority}>"
