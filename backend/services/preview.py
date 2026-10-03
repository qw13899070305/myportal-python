"""文件在线预览（对外门面）。

真正的实现已经拆成**可拆卸的预览扩展**，放在
:mod:`backend.extensions.preview` 里，每种格式一个文件：

    backend/extensions/preview/text.py     txt / md / csv / json / log
    backend/extensions/preview/image.py    png / jpg / gif / webp / bmp
    backend/extensions/preview/pdf.py      pdf（额外提供分页渲染）
    backend/extensions/preview/word.py     docx
    backend/extensions/preview/excel.py    xlsx
    backend/extensions/preview/ppt.py      pptx
    backend/extensions/preview/fallback.py 兜底提示

本模块保留了原有的函数名，历史代码与测试无需改动。
需要新增格式时，只要往那个目录里丢一个文件即可，不用动这里。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from backend.core.config import settings
from backend.core.utils import ALLOWED_ATTRIBUTES, ALLOWED_TAGS  # noqa: F401
from backend.extensions.preview import (  # noqa: F401
    PREVIEW_SECURITY_HEADERS,
    Preview,
    PreviewHandler,
    find_handler,
    registry,
    render_preview,
    supported_extensions,
)


def get_file_path(filename: str) -> Path:
    """把磁盘文件名解析成绝对路径，并校验未跳出上传目录。"""
    safe_name = Path(str(filename)).name
    base = settings.UPLOAD_DIR.resolve()
    fp = (base / safe_name).resolve()
    if not fp.is_relative_to(base):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not fp.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return fp


def _render_html(path: Path, ext: str) -> str:
    """渲染成 HTML 字符串；没有可用扩展时抛出 400。"""
    preview = render_preview(path, ext)
    if preview is None or preview.html is None:
        raise HTTPException(status_code=400, detail=f"{ext or '该'} 格式暂不支持在线预览")
    return preview.html


# ---------------- 各格式的便捷函数（保持原签名）----------------


def preview_text(file_path: Path) -> str:
    """纯文本 -> 转义后的 HTML。"""
    return _render_html(file_path, file_path.suffix.lower())


def preview_word(file_path: Path) -> str:
    """Word -> HTML（mammoth，缺失时退化为 python-docx）。"""
    return _render_html(file_path, ".docx")


def preview_excel(file_path: Path) -> str:
    """Excel -> HTML 表格。"""
    return _render_html(file_path, ".xlsx")


def preview_ppt(file_path: Path) -> str:
    """PowerPoint -> HTML。"""
    return _render_html(file_path, ".pptx")


# ---------------- PDF 相关（依赖 pdf 扩展的可选能力）----------------


def _pdf_handler():
    """取出声明了 PDF 能力的扩展；没有就 400。

    用鸭子类型而不是直接 import，这样删掉 pdf.py 也只影响 PDF 预览。
    """
    handler = find_handler(".pdf")
    if handler is None or not hasattr(handler, "render_page"):
        raise HTTPException(status_code=400, detail="当前未启用 PDF 预览扩展")
    return handler


def get_pdf_page_count(file_path: Path) -> int:
    """PDF 总页数。"""
    return _pdf_handler().page_count(file_path)


def preview_pdf_page(file_path: Path, page_num: int = 1) -> bytes:
    """把 PDF 的某一页渲染成 JPEG 字节流。"""
    return _pdf_handler().render_page(file_path, page_num)


__all__ = [
    "ALLOWED_ATTRIBUTES",
    "ALLOWED_TAGS",
    "PREVIEW_SECURITY_HEADERS",
    "Preview",
    "PreviewHandler",
    "find_handler",
    "get_file_path",
    "get_pdf_page_count",
    "preview_excel",
    "preview_pdf_page",
    "preview_ppt",
    "preview_text",
    "preview_word",
    "registry",
    "render_preview",
    "supported_extensions",
]
