"""把 :class:`Book`（纯数据）渲染成**网页预览**——网站专用的展示层。

这一层才是"前端"的事：HTML 外壳、CSS、中文文案都在这里。
手机 APP **不要**用这里的东西，它应该直接吃
``GET /api/v1/files/{id}/book`` 的 JSON，自己决定怎么画。

各格式的预览扩展只要继承 :class:`BookPreview` 声明扩展名即可，
展示逻辑只写这一遍。想换排版（比如加翻页、加朗读按钮）只改本文件，
解析层一行都不用动。
"""

from __future__ import annotations

from pathlib import Path

from backend.extensions.preview.base import Preview, PreviewHandler
from backend.services.books import Book, BookError, Chapter, parse_book

#: 阅读页样式：正文窄栏、衬线字体、深浅色自适应
_READING_STYLE = (
    ":root{color-scheme:light dark;}"
    "body{margin:0;padding:0;background:#faf9f7;color:#1f2328;}"
    ".book{max-width:44em;margin:0 auto;padding:28px 20px 60px;"
    "font-family:Georgia,'Songti SC','Noto Serif CJK SC',serif;"
    "font-size:17px;line-height:1.9;word-wrap:break-word;}"
    ".book-head{border-bottom:1px solid #e5e0d8;padding-bottom:16px;margin-bottom:24px;}"
    ".book-title{font-size:24px;margin:0 0 8px;line-height:1.4;}"
    ".book-meta{color:#6b7280;font-size:13px;margin:0;}"
    ".book-note{background:#fff7ed;color:#b45309;border-radius:8px;"
    "padding:10px 14px;font-size:14px;margin:16px 0;}"
    ".book-toc{background:#fff;border:1px solid #e5e0d8;border-radius:10px;"
    "padding:14px 18px;margin:0 0 28px;font-family:system-ui,sans-serif;font-size:14px;}"
    ".book-toc h2{margin:0 0 10px;font-size:15px;color:#6b7280;font-weight:600;}"
    ".book-toc ol{margin:0;padding-left:22px;}"
    ".book-toc li{margin:4px 0;}"
    ".book-toc a{color:#1d4ed8;text-decoration:none;}"
    ".book-chapter{margin:0 0 40px;}"
    ".book-chapter>h2{font-size:20px;border-left:4px solid #d1d5db;"
    "padding-left:10px;margin:32px 0 16px;}"
    ".book img{max-width:100%;height:auto;}"
    ".book table{border-collapse:collapse;margin:14px 0;width:100%;font-size:15px;}"
    ".book th,.book td{border:1px solid #d0d0d0;padding:6px 10px;text-align:left;}"
    ".book pre{background:#f3f4f6;padding:12px;overflow:auto;border-radius:6px;}"
    ".book blockquote{margin:14px 0;padding:6px 16px;border-left:3px solid #d1d5db;color:#4b5563;}"
    "@media (prefers-color-scheme:dark){"
    "body{background:#16181d;color:#e6e6e6;}"
    ".book-head{border-color:#2f333b;}.book-meta{color:#9aa1ac;}"
    ".book-toc{background:#1d2026;border-color:#2f333b;}.book-toc a{color:#7aa2f7;}"
    ".book-chapter>h2{border-color:#3a3f49;}.book th,.book td{border-color:#3a3f49;}"
    ".book pre{background:#22252b;}.book-note{background:#3a2c14;color:#f0b357;}}"
)


def _anchor_of(chapter: Chapter) -> str:
    """章节锚点：解析器给了就用它的，没给就按序号生成（保证唯一）。"""
    return chapter.anchor or f"chapter-{chapter.index}"


def _toc(chapters: tuple[Chapter, ...]) -> str:
    if len(chapters) < 2:
        return ""
    items = "".join(
        f"<li><a href='#{_anchor_of(chapter)}'>"
        f"{PreviewHandler.escape(chapter.title or f'第 {chapter.index + 1} 节')}</a></li>"
        for chapter in chapters
    )
    return f"<nav class='book-toc'><h2>目录（{len(chapters)}）</h2><ol>{items}</ol></nav>"


def _chapter_html(chapter: Chapter) -> str:
    title = PreviewHandler.escape(chapter.title) if chapter.title else ""
    heading = f"<h2>{title}</h2>" if title else ""
    return f"<section class='book-chapter' id='{_anchor_of(chapter)}'>{heading}{chapter.html}</section>"


def render_book_html(book: Book) -> str:
    """把一本书渲染成一个可滚动的 HTML 页面（目录 + 全部章节）。"""
    title = PreviewHandler.escape(book.title or "未命名")
    meta_bits = [PreviewHandler.escape(book.format.upper())]
    if book.author:
        meta_bits.append(PreviewHandler.escape(book.author))
    meta_bits.append(f"{book.chapter_count} 节")
    if book.language:
        meta_bits.append(PreviewHandler.escape(book.language))
    meta = " · ".join(meta_bits)

    notes = []
    if book.note:
        notes.append(PreviewHandler.escape(book.note))
    if book.truncated:
        notes.append("内容过大，仅显示前一部分，完整内容请下载查看。")
    note_html = f"<p class='book-note'>{' '.join(notes)}</p>" if notes else ""

    body = (
        "<div class='book'>"
        "<header class='book-head'>"
        f"<h1 class='book-title'>{title}</h1>"
        f"<p class='book-meta'>{meta}</p>"
        "</header>"
        f"{note_html}{_toc(book.chapters)}"
        f"{''.join(_chapter_html(chapter) for chapter in book.chapters)}"
        "</div>"
    )
    return (
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
        f"<style>{_READING_STYLE}</style></head><body>{body}</body></html>"
    )


class BookPreview(PreviewHandler):
    """书籍类预览扩展的公共基类：解析交给 ``services/books``，渲染交给本模块。"""

    priority = 20

    def render(self, path: Path) -> Preview:
        try:
            book = parse_book(path)
        except BookError as exc:
            return self.message_page("打不开这本书", exc.message)
        if book is None:  # pragma: no cover - 匹配到了就一定有解析器
            return self.message_page("暂不支持预览", "没有对应的书籍解析器。")
        return Preview.html_page(render_book_html(book))


__all__ = ["BookPreview", "render_book_html"]
