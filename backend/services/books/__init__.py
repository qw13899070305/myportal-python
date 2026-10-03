"""书籍解析服务（**纯数据层**，不产页面）。

分工（这条线就是"前后端分离"在文件层面的体现）：

============================  ==================================================
层                              职责
============================  ==================================================
``services/books/``            把 epub / azw3 / mobi / chm 解析成 :class:`Book`
                                —— 只有数据，没有 HTML 外壳、CSS、按钮文案
``extensions/preview/``        把 :class:`Book` 渲染成网页预览（网站专用）
``api/v1/file_book.py``        把 :class:`Book` 以 JSON 交给任何客户端（APP 用）
============================  ==================================================

一个新格式 = 本包下一个子包（或模块）+ 一个 :class:`BookParser` 子类，
放进来自动生效；删掉它只影响那一种格式。

注意：解析器**不要** import FastAPI / request / 预览扩展里的任何东西，
否则"后端 API 给 APP 用"这条线就被焊死了。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict
from pathlib import Path

from backend.core.logger import logger
from backend.extensions.registry import discover_extensions
from backend.services.books.model import Book, BookError, Chapter

#: 解析结果缓存条数。CHM 解一次 LZX 要几百毫秒，网页预览与 APP 各取一次
#: 不该解析两遍；Book 是不可变对象，可以安全共享。
_CACHE_LIMIT = 8
_cache: OrderedDict[tuple[str, int, int], Book] = OrderedDict()


class BookParser(ABC):
    """一个格式的解析器：输入文件路径，输出 :class:`Book`。"""

    #: 解析器名字（默认用类名），也是 ``Book.format`` 的取值
    name: str = ""
    #: 支持的扩展名（含点，小写）
    extensions: frozenset[str] = frozenset()
    #: 优先级，越大越先匹配
    priority: int = 0

    def matches(self, ext: str) -> bool:
        return ext in self.extensions

    @abstractmethod
    def parse(self, path: Path) -> Book:
        """解析文件；失败时抛 :class:`BookError`（带中文说明）。"""


def find_parser(ext: str) -> BookParser | None:
    """按扩展名找解析器，找不到返回 ``None``。"""
    for parser in registry.sorted_items(key=lambda item: -getattr(item, "priority", 0)):
        try:
            if parser.matches(ext):
                return parser
        except Exception as exc:  # pragma: no cover - 解析器自身实现有误
            logger.warning(f"书籍解析器 {parser!r} 匹配 {ext} 失败: {exc}")
    return None


def _cache_key(path: Path) -> tuple[str, int, int] | None:
    try:
        stat = path.stat()
    except OSError:  # pragma: no cover - 文件不在就没法缓存
        return None
    return (str(path), stat.st_mtime_ns, stat.st_size)


def clear_cache() -> None:
    """清空解析缓存（测试与"重新解析"场景用）。"""
    _cache.clear()


def parse_book(path: Path, ext: str | None = None, *, use_cache: bool = True) -> Book | None:
    """解析成 :class:`Book`；没有对应解析器返回 ``None``，失败抛 :class:`BookError`。

    同一个文件重复解析会命中缓存（键是路径 + mtime + 大小，文件一改就失效）。
    """
    suffix = (ext or path.suffix).lower()
    parser = find_parser(suffix)
    if parser is None:
        return None

    key = _cache_key(path) if use_cache else None
    if key is not None:
        cached = _cache.get(key)
        if cached is not None:
            _cache.move_to_end(key)
            return cached

    book = parser.parse(path)
    if book is None:  # pragma: no cover - 契约要求返回 Book
        raise BookError("解析器没有返回内容")

    if key is not None:
        _cache[key] = book
        while len(_cache) > _CACHE_LIMIT:
            _cache.popitem(last=False)
    return book


def supported_extensions() -> set[str]:
    """所有解析器声明支持的扩展名。"""
    result: set[str] = set()
    for parser in registry:
        result |= set(getattr(parser, "extensions", ()) or ())
    return result


# ---------------- 解析器发现 ----------------
# 必须放在**所有类/函数定义之后**：discover 会立刻 import 包内的解析器模块，
# 而那些模块要 ``from backend.services.books import BookParser``。
# 如果这行在前面，包还处于半初始化状态，子模块只能拿到 ImportError，
# 而 discover 的容错又会把它记成一条 warning 静默跳过 —— 解析器全都注册不上。
#: 解析器注册表（与预览扩展同一套可拆卸机制）
registry = discover_extensions(
    __name__,
    "book",
    "书籍解析器",
    skip={"model", "sanitize"},
)


__all__ = [
    "Book",
    "BookError",
    "BookParser",
    "Chapter",
    "clear_cache",
    "find_parser",
    "parse_book",
    "registry",
    "supported_extensions",
]
