"""PDF 预览扩展。

除了内联展示，还额外提供两个**可选能力**：

- ``page_count(path)`` —— PDF 总页数
- ``render_page(path, n)`` —— 把第 n 页渲染成 JPEG 字节

接口层通过 ``getattr(handler, "page_count", None)`` 这种鸭子类型来调用，
所以把本文件删掉之后，PDF 会退回"直接内联下载"，其余功能不受影响。
"""

from __future__ import annotations

from pathlib import Path

from backend.extensions.preview.base import Preview, PreviewHandler
from backend.extensions.registry import get_registry


def _import_pymupdf():
    """PyMuPDF 新版推荐 ``import pymupdf``，旧版本只有 ``fitz``。"""
    try:
        import pymupdf as fitz  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - 旧版本回退
        import fitz  # type: ignore[no-redef]
    return fitz


class PdfPreview(PreviewHandler):
    name = "pdf"
    extensions = frozenset({".pdf"})
    priority = 10

    media_type = "application/pdf"
    #: 分页渲染的分辨率
    dpi = 150

    def render(self, path: Path) -> Preview:
        return Preview.inline_file(self.media_type)

    # ---------------- 可选能力 ----------------

    def page_count(self, path: Path) -> int:
        """PDF 总页数。"""
        fitz = _import_pymupdf()
        with fitz.open(str(path)) as doc:
            return doc.page_count

    def render_page(self, path: Path, page_num: int = 1) -> bytes:
        """把指定页渲染成 JPEG；页码越界抛 ``ValueError``。"""
        fitz = _import_pymupdf()
        with fitz.open(str(path)) as doc:
            if page_num < 1 or page_num > doc.page_count:
                raise ValueError("页码超出范围")
            page = doc.load_page(page_num - 1)
            return page.get_pixmap(dpi=self.dpi).tobytes("jpg")


get_registry("preview").register(PdfPreview())
