"""纯文本类文件的预览扩展。

支持：txt / md / csv / json / log
策略：整体 HTML 转义后用等宽字体原样展示（绝不允许原文里的标签生效）。
"""

from __future__ import annotations

from pathlib import Path

from backend.extensions.preview.base import Preview, PreviewHandler
from backend.extensions.registry import get_registry


class TextPreview(PreviewHandler):
    name = "text"
    extensions = frozenset({".txt", ".md", ".csv", ".json", ".log"})
    priority = 10

    #: 单次最多渲染的字符数，避免超大日志把浏览器卡死
    max_chars = 200_000

    def render(self, path: Path) -> Preview:
        text = path.read_text(encoding="utf-8", errors="replace")
        truncated = len(text) > self.max_chars
        if truncated:
            text = text[: self.max_chars]

        escaped = self.escape(text)
        note = (
            "<p style='color:#b45309'>文件过大，仅显示前 "
            f"{self.max_chars} 个字符，完整内容请下载查看。</p>"
            if truncated
            else ""
        )
        body = (
            "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            "<style>body{margin:0;padding:16px;font-family:ui-monospace,Menlo,"
            "Consolas,monospace;font-size:13px;line-height:1.6;white-space:pre-wrap;"
            "word-break:break-word;}</style>"
            f"</head><body>{note}{escaped}</body></html>"
        )
        return Preview.html_page(body)


get_registry("preview").register(TextPreview())
