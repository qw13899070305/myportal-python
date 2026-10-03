"""书籍数据的**纯模型**——跟格式无关，跟界面更无关。

这一层只说"书里有什么"，不说"长什么样"。因此：

- 网页预览（``backend/extensions/preview/``）把 :class:`Book` 渲染成 HTML 页面
- 手机 APP 直接消费 ``GET /api/v1/files/{id}/book`` 返回的 JSON
- 以后要加"导出 TXT"、"语音朗读"、"全文检索"，都只是 Book 的另一个消费者

解析器**不许**在这一层写 HTML 外壳、CSS、按钮文案。
改本文件等于改接口，改之前先想清楚下游有谁。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Chapter:
    """一章 / 一节 / 一个主题页。

    ``html`` 必须是**已经清洗过**的安全片段（白名单标签，图片已内联成
    ``data:`` URI），客户端可以直接塞进 WebView；``text`` 是同一段内容的
    纯文本，给原生界面、搜索、朗读用。
    """

    index: int
    title: str = ""
    html: str = ""
    text: str = ""
    #: 页内锚点（网页渲染器用；由解析器保证全局唯一）
    anchor: str = ""

    def to_json(self, *, include_html: bool = True, include_text: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {"index": self.index, "title": self.title, "anchor": self.anchor}
        if include_html:
            data["html"] = self.html
        if include_text:
            data["text"] = self.text
        return data


@dataclass(frozen=True)
class Book:
    """一本解析好的书（不可变，解析器一次产出，多个客户端各取所需）。"""

    #: 解析器名字，也是格式标识：epub / mobi / chm
    format: str
    title: str = ""
    author: str = ""
    language: str = ""
    chapters: tuple[Chapter, ...] = field(default_factory=tuple)
    #: 是否命中体积/数量上限被截断（客户端应提示"仅显示前一部分"）
    truncated: bool = False
    #: 给用户看的一句补充说明（可为空）。不是排版，是数据自带的告示
    note: str = ""

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)

    @property
    def char_count(self) -> int:
        return sum(len(chapter.text) for chapter in self.chapters)

    def to_json(
        self,
        *,
        include_html: bool = True,
        include_text: bool = True,
        chapters: tuple[Chapter, ...] | None = None,
    ) -> dict[str, Any]:
        """序列化成 API 响应（字段名即对外契约）。"""
        picked = self.chapters if chapters is None else chapters
        return {
            "format": self.format,
            "title": self.title,
            "author": self.author,
            "language": self.language,
            "chapter_count": self.chapter_count,
            "truncated": self.truncated,
            "note": self.note,
            "chapters": [
                chapter.to_json(include_html=include_html, include_text=include_text)
                for chapter in picked
            ],
        }


class BookError(Exception):
    """解析失败（文件损坏 / 加密 / 不支持的变体）。

    ``message`` 是可以直接展示给用户的中文说明；``drm`` 区分"加密打不开"
    与"格式不认识"，客户端可以据此给不同提示。
    """

    def __init__(self, message: str, *, drm: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.drm = drm


__all__ = ["Book", "BookError", "Chapter"]
