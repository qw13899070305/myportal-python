"""文件在线预览扩展包。

每种文档格式都是**一个可以单独摘掉的模块**：

======================  ==============================
模块                     负责的格式
======================  ==============================
``text.py``              txt / md / csv / json / log
``image.py``             png / jpg / gif / webp / bmp
``pdf.py``               pdf（含分页渲染能力）
``word.py``              docx
``excel.py``             xlsx
``ppt.py``               pptx
``fallback.py``          兜底：不支持的格式给出提示页
======================  ==============================

删掉 ``word.py``，Word 预览会退回兜底提示页，其它格式照常工作。
"""

from __future__ import annotations

from pathlib import Path

from backend.core.logger import logger
from backend.extensions.preview.base import (
    PREVIEW_SECURITY_HEADERS,
    Preview,
    PreviewHandler,
)
from backend.extensions.registry import discover_extensions

#: 导入包内所有扩展模块（``base`` 只放基类，跳过）
registry = discover_extensions(__name__, "preview", "文件在线预览扩展", skip={"base"})


def find_handler(ext: str) -> PreviewHandler | None:
    """按扩展名找预览扩展，找不到返回 None。

    按 ``priority`` 从高到低匹配，因此兜底扩展（负优先级）只在
    没有任何具体格式扩展认领时才生效。
    """
    for handler in registry.sorted_items(key=lambda item: -getattr(item, "priority", 0)):
        try:
            if handler.matches(ext):
                return handler
        except Exception as exc:  # pragma: no cover - 扩展自身实现有误
            logger.warning(f"预览扩展 {handler!r} 匹配 {ext} 失败: {exc}")
    return None


def render_preview(path: Path, ext: str) -> Preview | None:
    """渲染预览；扩展内部抛异常时返回 None，由调用方决定怎么兜底。"""
    handler = find_handler(ext)
    if handler is None:
        return None
    try:
        return handler.render(path)
    except Exception as exc:
        logger.warning(f"预览扩展 {handler!r} 渲染 {path.name} 失败: {exc}")
        return None


def handler_for(ext: str) -> PreviewHandler | None:
    """公共别名，语义更直观。"""
    return find_handler(ext)


def supported_extensions() -> set[str]:
    """所有扩展件声明支持的扩展名（兜底扩展不计入）。"""
    result: set[str] = set()
    for handler in registry:
        result |= set(getattr(handler, "extensions", ()) or ())
    return result


__all__ = [
    "PREVIEW_SECURITY_HEADERS",
    "Preview",
    "PreviewHandler",
    "find_handler",
    "handler_for",
    "registry",
    "render_preview",
    "supported_extensions",
]
