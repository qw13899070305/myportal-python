"""预览扩展的基类与公共工具。

一个预览扩展 = 一个模块 + 一个 :class:`PreviewHandler` 子类。
把文件删掉，对应格式就自然"不支持预览"，其它格式完全不受影响。
"""

from __future__ import annotations

import html as html_lib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

#: 预览响应统一附加的安全头（阻止文档内脚本执行）
PREVIEW_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
}

#: 认为"看起来像资源文件"的路径（用于 SPA 静态资源回退判断）
_STYLE = (
    "body{font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',sans-serif;"
    "line-height:1.7;padding:20px;color:#111;background:#fff;}"
    "table{border-collapse:collapse;margin:12px 0;width:100%;}"
    "th,td{border:1px solid #d0d0d0;padding:6px 10px;text-align:left;font-size:14px;}"
    "th{background:#f5f5f5;}"
    "h1,h2,h3{line-height:1.35;}"
    "img{max-width:100%;height:auto;}"
    "pre{background:#f6f6f6;padding:12px;overflow:auto;}"
)


@dataclass(frozen=True)
class Preview:
    """一次预览的结果。

    - ``kind="file"``：直接把磁盘文件内联返回（图片 / PDF）
    - ``kind="html"``：返回已经清洗过的 HTML
    """

    kind: str
    html: str | None = None
    media_type: str | None = None

    @classmethod
    def inline_file(cls, media_type: str) -> Preview:
        return cls(kind="file", media_type=media_type)

    @classmethod
    def html_page(cls, body: str) -> Preview:
        return cls(kind="html", html=body)


class PreviewHandler(ABC):
    """预览扩展基类。

    子类只需要声明 :attr:`name` / :attr:`extensions` 并实现 :meth:`render`。
    """

    #: 扩展件名称（默认用类名）
    name: str = ""
    #: 支持的扩展名（含点，小写）
    extensions: frozenset[str] = frozenset()
    #: 优先级，越大越先被匹配（兜底扩展用负数）
    priority: int = 0

    def matches(self, ext: str) -> bool:
        """默认按扩展名匹配，兜底扩展可以覆写为恒真。"""
        return ext in self.extensions

    @abstractmethod
    def render(self, path: Path) -> Preview:
        """把文件渲染成预览结果。"""

    # ---------------- 供子类复用的工具 ----------------

    @staticmethod
    def wrap_html(body: str) -> str:
        """套上统一的外壳与内联样式（在 iframe 中直接展示）。"""
        return (
            "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            f"<style>{_STYLE}</style></head><body>{body}</body></html>"
        )

    @staticmethod
    def escape(value: object) -> str:
        return html_lib.escape(str(value))

    @staticmethod
    def message_page(title: str, detail: str) -> Preview:
        """生成一个提示页（用于"暂不支持预览"这类降级）。"""
        body = (
            "<div style='padding:40px;text-align:center;color:#666'>"
            f"<p style='font-size:18px'>{html_lib.escape(title)}</p>"
            f"<p>{html_lib.escape(detail)}</p></div>"
        )
        return Preview.html_page(PreviewHandler.wrap_html(body))

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        exts = ",".join(sorted(self.extensions)) or "*"
        return f"<{type(self).__name__} {self.name or ''} [{exts}]>"
