"""EPUB（.epub）在线预览扩展。

解析在 :mod:`backend.services.books.epub`（纯数据），网页渲染在
:mod:`backend.extensions.preview.book_base`（网站专用展示层）。
本文件只是把两者接起来的**薄适配器**：声明扩展名即可，
排版要改就改 ``book_base.py``，手机 APP 则完全不经过这里。

优先级继承自 :class:`BookPreview`（20，高于 text/image 的 10，远高于兜底的 -100）。
删掉本文件，.epub 会退回"暂不支持在线预览"，其它格式不受影响。
"""

from __future__ import annotations

from backend.extensions.preview.book_base import BookPreview
from backend.extensions.registry import get_registry


class EpubPreview(BookPreview):
    name = "epub"
    extensions = frozenset({".epub"})


get_registry("preview").register(EpubPreview())
