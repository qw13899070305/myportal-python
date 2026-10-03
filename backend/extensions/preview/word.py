"""Word（.docx）预览扩展。

优先用 mammoth 转 HTML（效果好），缺少该依赖时退化为 python-docx 逐段取文本。
mammoth 的输出会经过 bleach 白名单清洗，防止恶意文档注入脚本。
"""

from __future__ import annotations

from pathlib import Path

from backend.core.utils import sanitize_html_bleach
from backend.extensions.preview.base import Preview, PreviewHandler
from backend.extensions.registry import get_registry


class WordPreview(PreviewHandler):
    name = "word"
    extensions = frozenset({".docx"})
    priority = 10

    def render(self, path: Path) -> Preview:
        try:
            import mammoth
        except ImportError:
            return self._render_with_python_docx(path)

        with open(path, "rb") as handle:
            result = mammoth.convert_to_html(handle)
        # mammoth 的输出可能含脚本/事件属性，必须清洗
        body = f"<div class='preview-container'>{sanitize_html_bleach(result.value)}</div>"
        return Preview.html_page(self.wrap_html(body))

    # ---------------- 降级实现 ----------------

    def _render_with_python_docx(self, path: Path) -> Preview:
        from docx import Document

        document = Document(str(path))
        parts = ["<div class='preview-container'>"]
        for paragraph in document.paragraphs:
            text = self.escape(paragraph.text)
            parts.append(f"<p>{text}</p>" if text else "<p>&nbsp;</p>")
        parts.append("</div>")
        return Preview.html_page(self.wrap_html("".join(parts)))


get_registry("preview").register(WordPreview())
