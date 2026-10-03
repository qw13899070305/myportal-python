"""MOBI / AZW3 解析过程中的**内部**异常。

这些异常只在解析包内部流转：:class:`~backend.services.books.mobi.MobiParser`
会接住它们，翻译成模型层的 :class:`~backend.services.books.model.BookError`。
所以这里的文字是**技术原因**，面向用户的中文说明统一写在解析器边界上，
低层模块不写提示文案。
"""

from __future__ import annotations


class MobiFormatError(Exception):
    """结构不对：文件损坏、不是 MOBI、字段越界……"""


class DrmProtected(MobiFormatError):
    """书带 DRM，正文解不开。"""


class UnsupportedFeature(MobiFormatError):
    """格式本身没问题，但本解析器目前解不了（例如 HUFF/CDIC 表不可用）。"""


__all__ = ["DrmProtected", "MobiFormatError", "UnsupportedFeature"]
