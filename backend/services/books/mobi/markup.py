"""正文标记 → 干净的 HTML 片段（MOBI 的"半 HTML"）。

KF8 段是 XHTML，MOBI 6 段是老式 Mobipocket 标记，两者都可能出现：

- ``<mbp:pagebreak/>``、``<o:p>`` 这类非标准 / 带命名空间的标签 —— 清掉
- ``<img recindex="00001">`` —— 换成内联的 ``data:`` 图片（定位不到就整条删掉）
- ``<a filepos=...>`` —— 属性不在白名单里，交给共用清洗器丢掉

清洗一律走 :mod:`backend.services.books.sanitize`，本模块自己不做白名单。
图片记录由调用方通过 :func:`image_inliner` 提供的映射函数给出，
所以这里不需要认识 PalmDB 的细节。
"""

from __future__ import annotations

import html as html_lib
import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from backend.services.books.sanitize import clean_html, data_uri

if TYPE_CHECKING:  # 只为类型标注，运行时不依赖容器层
    from backend.services.books.mobi.header import Section
    from backend.services.books.mobi.pdb import PalmDatabase

#: 整本最多内联多少图片字节（base64 之后还会再涨约 1/3）
MAX_INLINE_TOTAL_BYTES = 4 * 1024 * 1024
#: 单张图片上限
MAX_INLINE_IMAGE_BYTES = 2 * 1024 * 1024

#: 分章用的分页 / 分节标记：
#: - ``<mbp:pagebreak/>``：老式 MOBI 6 的标准分页
#: - ``class="...mbp_pagebreak..."``：KF8 里等价的写法
#: - ``class="chapter"``：EPUB/kindlegen 转出来的 KF8 常用结构
#:   （实测 Gutenberg 的 azw3 就是 ``<div class="chapter">``，一章一个；
#:   注意不能按 ``id="calibre_pb_N"`` 切——那个 id 长在标签内部，切开就毁标签）
_CHAPTER_BREAK_RE = re.compile(
    r"<mbp:pagebreak\b[^>]*>"
    r"|<[a-z][\w:-]*\b[^>]*\bclass\s*=\s*[\"'][^\"']*\bmbp_pagebreak\b[^\"']*[\"'][^>]*>"
    r"|<[a-z][\w:-]*\b[^>]*\bclass\s*=\s*[\"'](?:[^\"']*\s)?chapter(?:\s[^\"']*)?[\"'][^>]*>",
    re.IGNORECASE,
)
#: 带命名空间的标签（含 <mbp:...>）：标签名本身带冒号才算，避免误伤 href="http://…"
_NAMESPACE_TAG_RE = re.compile(r"</?\s*[A-Za-z_][\w.-]*:[^>\s/>]*[^>]*>")
#: KF8 的 <head> 里只有 <title>/<link>/<guide> 这类元数据，整段去掉；
#: 共用清洗器只 strip 标签不删内容，留着会把内部标题漏成正文
_HEAD_ELEMENT_RE = re.compile(r"<head\b[^>]*>.*?</head\s*>", re.IGNORECASE | re.DOTALL)
#: 会被清洗器整段丢掉的标签，这里先收掉它们的"单标签"形式
_HEADING_RE = re.compile(r"<h[1-6]\b[^>]*>(.*?)</h[1-6]\s*>", re.IGNORECASE | re.DOTALL)
#: 找"开头第一个块"用的标签（MOBI 6 没有标题标签，只能看首个段落）
_BLOCK_RE = re.compile(r"<(p|div|td|li|h[1-6])\b[^>]*>(.*?)</\1\s*>", re.IGNORECASE | re.DOTALL)
#: 章节名的长度上限：首块超过它说明是正文，宁可不给标题
_MAX_TITLE_CHARS = 60

_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_RECINDEX_RE = re.compile(r"""recindex\s*=\s*["']?\s*(\d+)""", re.IGNORECASE)
_SRC_RE = re.compile(r"""src\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
_ALT_RE = re.compile(r"""alt\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
_DIGITS_RE = re.compile(r"\d+")
#: KF8 里图片 src 的常见写法：kindle:embed:0001 / image00004.jpeg / 00004.jpg
_SRC_HINT_RE = re.compile(r"embed|image|\d+\.(?:jpe?g|png|gif|bmp|webp)", re.IGNORECASE)

#: 图片魔数 -> MIME（记录里没有文件名，只能靠魔数认）
_IMAGE_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
)


def sniff_image(data: bytes) -> str | None:
    """按魔数认图片类型，认不出就说明这条记录不是图片。"""
    for magic, mime in _IMAGE_MAGIC:
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def image_inliner(
    database: PalmDatabase, section: Section, max_image_bytes: int = MAX_INLINE_IMAGE_BYTES
) -> Callable[[int], str | None]:
    """造一个"recindex -> data URI"的映射函数。

    MOBI 的 ``<img recindex="N">`` 指向第 ``first_image_index + N - 1`` 条记录；
    KF8 段的这个字段有时相对本段起算，所以两种解释都试，用图片魔数确认。
    定位不到（或超出预算）返回 ``None``，由调用方删掉图片标签。
    """
    header = section.mobi
    budget = MAX_INLINE_TOTAL_BYTES

    def resolve(number: int) -> str | None:
        nonlocal budget
        if header is None or number <= 0 or header.first_image_index <= 0:
            return None
        absolute = header.first_image_index + number - 1
        for index in (absolute, section.image_bias + absolute):
            if index < 0 or index >= len(database):
                continue
            record = database.record(index)
            if not record or len(record) > max_image_bytes:
                continue
            mime = sniff_image(record)
            if mime is None:
                continue
            uri = data_uri(record, mime)
            if len(uri) > budget:
                return None
            budget -= len(uri)
            return uri
        return None

    return resolve


def inline_images(markup: str, resolve: Callable[[int], str | None] | None) -> str:
    """把 ``<img>`` 换成内联图片；定位不到就删掉标签（只留 alt 文字）。"""

    def replace(match: re.Match[str]) -> str:
        tag = match.group(0)
        uri = None
        if resolve is not None:
            for number in _image_numbers(tag):
                uri = resolve(number)
                if uri is not None:
                    break
        if uri is None:
            alt = _ALT_RE.search(tag)
            return html_lib.escape(alt.group(1)) if alt else ""
        alt = _ALT_RE.search(tag)
        label = f" alt=\"{html_lib.escape(alt.group(1))}\"" if alt else ""
        return f'<img src="{uri}"{label} />'

    return _IMG_RE.sub(replace, markup)


def _image_numbers(tag: str) -> list[int]:
    """从 ``<img>`` 里猜图片序号：recindex 优先，其次是 KF8 的 src 写法。"""
    numbers: list[int] = []
    recindex = _RECINDEX_RE.search(tag)
    if recindex is not None:
        numbers.append(int(recindex.group(1)))
    source = _SRC_RE.search(tag)
    if source is not None and "flow" not in source.group(1).lower():
        # kindle:flow:... 是排版流（SVG 封面之类），不对应图片记录
        if _SRC_HINT_RE.search(source.group(1)):
            digits = _DIGITS_RE.search(source.group(1))
            if digits is not None:
                numbers.append(int(digits.group(0)))
    return numbers


def strip_namespace_tags(markup: str) -> str:
    """去掉 ``<mbp:pagebreak/>``、``<o:p>`` 这类非标准标签与 XHTML 的 ``<head>``。"""
    return _NAMESPACE_TAG_RE.sub("", _HEAD_ELEMENT_RE.sub("", markup))


def plain_text_to_html(text: str) -> str:
    """完全没有标签的老式正文（纯文本 PalmDOC）：转义后按空行分段。"""
    blocks = []
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        if not paragraph.strip():
            continue
        escaped = html_lib.escape(paragraph.strip()).replace("\n", "<br>")
        blocks.append(f"<p>{escaped}</p>")
    return "".join(blocks)


def fragment_to_html(markup: str, resolve: Callable[[int], str | None] | None = None) -> str:
    """一段正文标记 -> 清洗过的安全 HTML 片段。"""
    if "<" not in markup:
        fragment = plain_text_to_html(markup)
    else:
        fragment = strip_namespace_tags(markup)
        fragment = inline_images(fragment, resolve)
    return clean_html(fragment)


def split_chapters(markup: str) -> list[str]:
    """按分页标记切章；切不动就整本一段（返回单元素列表）。"""
    parts = [part for part in _CHAPTER_BREAK_RE.split(markup) if part and part.strip()]
    return parts or [markup]


def _plain_text(fragment: str) -> str:
    """标签剥掉、实体还原、空白压成一个空格。"""
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html_lib.unescape(text)).strip()


def chapter_title(fragment: str) -> str:
    """取章节名：优先第一个 ``h1``~``h6``。

    老式 MOBI 6（比如 Gutenberg 的 .mobi）根本没有标题标签，书名/章名是用
    ``<font size="7">`` 排的，所以退一步取开头第一个**短**段落当标题；
    第一个块就是长段落说明那是正文，宁可不给标题（返回空串）。
    """
    heading = _HEADING_RE.search(fragment)
    if heading is not None:
        return _plain_text(heading.group(1))[:120]
    for block in _BLOCK_RE.finditer(fragment[:3000]):
        text = _plain_text(block.group(2))
        if not text:
            continue
        return text if len(text) <= _MAX_TITLE_CHARS else ""
    return ""


__all__ = [
    "MAX_INLINE_IMAGE_BYTES",
    "MAX_INLINE_TOTAL_BYTES",
    "chapter_title",
    "fragment_to_html",
    "image_inliner",
    "inline_images",
    "plain_text_to_html",
    "sniff_image",
    "split_chapters",
    "strip_namespace_tags",
]
