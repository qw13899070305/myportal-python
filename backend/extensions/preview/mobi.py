"""Kindle 电子书（.azw3 / .mobi）预览扩展。

这里只剩"接线"：解析交给 ``backend/services/books/mobi/``（纯数据层），
渲染交给共用的 :class:`~backend.extensions.preview.book_base.BookPreview`
（HTML 外壳、CSS、目录、提示文案都在那边）。

删掉本文件，AZW3 / MOBI 退回兜底提示页，而解析服务与 APP 的 JSON 接口
不受任何影响。
"""

from __future__ import annotations

from backend.extensions.preview.book_base import BookPreview
from backend.extensions.registry import get_registry


class MobiPreview(BookPreview):
    """AZW3（KF8）/ MOBI 6 在线阅读预览。"""

    name = "mobi"
    extensions = frozenset({".azw3", ".mobi"})


get_registry("preview").register(MobiPreview())
