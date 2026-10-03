"""章节图片：在 zip 里定位 → 内联成 ``data:`` URI。

定位顺序（书里的 ``src`` 都是相对路径，而且经常写错）：

1. 相对当前章节所在目录解析
2. 找不到再全局按文件名兜底

能不能内联、多大算太大，由 :mod:`backend.services.books.sanitize` 说了算
（白名单类型 + 单张上限）；"整本书一共能内联多少"由 :class:`InlineBudget`
记账 —— 漫画、扫描版很容易几十 MB，不能无限往里塞 ``data:``。
超预算的图片返回 ``None``，由调用方（:mod:`.chapters`）留一句占位说明。
"""

from __future__ import annotations

import re

from backend.services.books.sanitize import (
    IMAGE_MIME_TYPES,
    MAX_INLINE_IMAGE_BYTES,
    inline_image,
)

from .container import EpubContainer, book_path

#: 书里自带的 ``data:`` 图片（少见，但确实有），识别出来同样算预算
_DATA_URI_RE = re.compile(r"^data:([\w.+-]+/[\w.+-]+);base64,([A-Za-z0-9+/=\s]+)$", re.I)
_IMAGE_MIME_VALUES = frozenset(IMAGE_MIME_TYPES.values())


class InlineBudget:
    """整本书的图片内联预算。"""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0

    def take(self, size: int) -> bool:
        """装得下就记账并返回 ``True``。"""
        if size <= 0 or size > MAX_INLINE_IMAGE_BYTES or self.used + size > self.limit:
            return False
        self.used += size
        return True


def inline_source(
    container: EpubContainer, src: str, chapter_path: str, budget: InlineBudget
) -> str | None:
    """把 ``<img src>`` 换成 ``data:`` URI；找不到 / 类型不认识 / 超预算返回 ``None``。"""
    src = (src or "").strip()
    if not src:
        return None
    if src.lower().startswith("data:"):
        return _keep_existing(src, budget)
    name = container.resolve(book_path(chapter_path, src))
    if name is None:
        name = container.resolve_by_basename(src)
    if name is None:
        return None
    data = container.read(name)
    if data is None:
        return None
    uri = inline_image(data, name)
    if uri is None or not budget.take(len(data)):
        return None
    return uri


def _keep_existing(src: str, budget: InlineBudget) -> str | None:
    """已经是 ``data:`` 的图片原样保留（但类型要认识、也要占预算）。"""
    match = _DATA_URI_RE.match(src)
    if match is None or match.group(1).lower() not in _IMAGE_MIME_VALUES:
        return None
    return src if budget.take(len(match.group(2)) * 3 // 4) else None


__all__ = ["InlineBudget", "inline_source"]
