"""CHM（Windows 帮助文件）网页预览扩展。

解析（LZX 解压、目录树、正文清洗）全在
:mod:`backend.services.books.chm` 里，产出纯数据的 ``Book``；
本模块只声明扩展名，"怎么用网页展示这本书"由
:mod:`backend.extensions.preview.book_base` 统一负责——想换排版只改那一处。
"""

from __future__ import annotations

from backend.extensions.preview.book_base import BookPreview
from backend.extensions.registry import get_registry


class ChmPreview(BookPreview):
    name = "chm"
    extensions = frozenset({".chm"})


get_registry("preview").register(ChmPreview())
