"""共用 HTML 清洗工具（纯函数，与格式无关）。

电子书 / CHM 里拿到的 HTML 一律先过这里，再交给任何客户端：

- 只保留白名单标签与属性
- ``script`` / ``style`` / ``iframe`` / ``object`` 这类**连同内容一起丢掉**
  （只 strip 标签会把 CSS/JS 源码漏成正文）
- ``href`` / ``src`` 只允许 ``http`` / ``https`` / ``mailto`` / ``data``
  （``data`` 是给内联图片用的，解析器自己生成）
- ``style`` 属性交给 bleach 的 CSSSanitizer 逐条声明过滤

这里**不做**格式相关的事（不去 zip 里找图片、不认识 ``recindex``、
不认识 ``ms-its:``）——那些是各格式解析器的活。
"""

from __future__ import annotations

import base64
import html as html_lib
import re

import bleach
from bleach.css_sanitizer import CSSSanitizer

#: 正文白名单：结构 + 排版，不含任何可执行或可自动外链加载的东西。
#: 旧电子书里常见的 ``font`` / ``center`` 也留着，否则排版会散架。
CONTENT_TAGS: frozenset[str] = frozenset(
    {
        "a", "abbr", "article", "aside", "b", "big", "blockquote", "br",
        "caption", "center", "cite", "code", "col", "colgroup", "dd", "del",
        "dfn", "div", "dl", "dt", "em", "figcaption", "figure", "font",
        "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "i",
        "img", "ins", "kbd", "li", "main", "mark", "nav", "ol", "p", "pre",
        "q", "s", "samp", "section", "small", "span", "strike", "strong",
        "sub", "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr",
        "tt", "u", "ul", "var", "wbr",
    }
)

#: 属性白名单。默认**不给 id**：多章拼成一页时书里的 id 会互相打架，
#: 锚点由解析器自己套在外层容器上。
CONTENT_ATTRIBUTES: dict[str, list[str]] = {
    "*": ["class", "title", "dir", "lang", "align", "style"],
    "a": ["href", "name"],
    "img": ["src", "alt", "width", "height"],
    "table": ["border", "cellpadding", "cellspacing", "width", "summary"],
    "col": ["span", "width"],
    "colgroup": ["span", "width"],
    "td": ["colspan", "rowspan", "valign", "width", "height"],
    "th": ["colspan", "rowspan", "valign", "width", "height"],
    "ol": ["start", "type"],
    "li": ["value"],
    "font": ["color", "face", "size"],
}

#: 允许的 URL 协议
ALLOWED_PROTOCOLS: frozenset[str] = frozenset({"http", "https", "mailto", "data"})

#: 图片 MIME 白名单（内联用；不含 svg —— svg 能带脚本）
IMAGE_MIME_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}

#: 单张图片内联上限（超过就留占位说明，别把页面撑爆）
MAX_INLINE_IMAGE_BYTES = 2 * 1024 * 1024

#: 这些标签连同内容一起删（正则兜底，处理未闭合/畸形的情况）。
#: ``head`` / ``title`` 也在里面：解析器如果一时大意把整篇文档丢进来，
#: 标题与 meta 的文字不能漏成正文（各解析器自己的标题提取要在清洗**之前**做）。
_DROP_WITH_CONTENT = re.compile(
    r"<(script|style|head|title|iframe|object|embed|applet|form|input|button|"
    r"select|textarea|noscript|svg|math|template|link|meta|base)\b.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
#: 上面那批标签的自闭合 / 单个出现形式
_DROP_SELF = re.compile(
    r"<(script|style|head|title|iframe|object|embed|applet|form|input|button|"
    r"select|textarea|noscript|svg|math|template|link|meta|base)\b[^>]*/?>",
    re.IGNORECASE,
)
_DROP_COMMENTS = re.compile(r"<!--.*?-->", re.DOTALL)
_DROP_DECL = re.compile(r"<[!?][^>]*>", re.DOTALL)

#: bleach 官方说明 Cleaner 可复用（clean() 每次自己建解析器）
_CLEANER = bleach.Cleaner(
    tags=CONTENT_TAGS,
    attributes=CONTENT_ATTRIBUTES,
    protocols=ALLOWED_PROTOCOLS,
    css_sanitizer=CSSSanitizer(),
    strip=True,
    strip_comments=True,
)

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"[ \t\r\f\v]+")


def drop_dangerous_blocks(fragment: str) -> str:
    """先把"危险标签连同内容"整段删掉，再交给 bleach 逐标签清洗。"""
    text = _DROP_COMMENTS.sub(" ", fragment)
    text = _DROP_DECL.sub(" ", text)
    text = _DROP_WITH_CONTENT.sub(" ", text)
    return _DROP_SELF.sub(" ", text)


def clean_html(
    fragment: str,
    *,
    extra_tags: frozenset[str] | set[str] = frozenset(),
    extra_attributes: dict[str, list[str]] | None = None,
) -> str:
    """清洗一段正文 HTML，返回可安全交给任何客户端的片段。

    ``extra_tags`` / ``extra_attributes`` 只用于少数格式的特殊需要
    （例如 CHM 想保留 ``id``），这些额外项**必须**同样是无害的。
    """
    prepared = drop_dangerous_blocks(fragment or "")
    if not extra_tags and not extra_attributes:
        return _CLEANER.clean(prepared)

    tags = set(CONTENT_TAGS) | set(extra_tags)
    attributes: dict[str, list[str]] = {k: list(v) for k, v in CONTENT_ATTRIBUTES.items()}
    for tag, attrs in (extra_attributes or {}).items():
        merged = attributes.setdefault(tag, [])
        for attr in attrs:
            if attr not in merged:
                merged.append(attr)
    cleaner = bleach.Cleaner(
        tags=tags,
        attributes=attributes,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=CSSSanitizer(),
        strip=True,
        strip_comments=True,
    )
    return cleaner.clean(prepared)


def strip_tags(fragment: str) -> str:
    """把 HTML 变成纯文本（``text`` 字段用，给原生界面/搜索/朗读）。"""
    text = _DROP_WITH_CONTENT.sub(" ", fragment or "")
    text = _DROP_SELF.sub(" ", text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|h[1-6]|tr)\s*>", "\n", text, flags=re.IGNORECASE)
    text = _TAG_RE.sub("", text)
    text = html_lib.unescape(text)
    text = _SPACE_RE.sub(" ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def guess_image_mime(name: str) -> str | None:
    """按扩展名判断能不能内联成 ``data:`` 图片，不能就返回 ``None``。"""
    dot = str(name).rfind(".")
    if dot < 0:
        return None
    return IMAGE_MIME_TYPES.get(str(name)[dot:].lower())


def data_uri(data: bytes, mime: str) -> str:
    """把二进制内联成 ``data:`` URI（图片必须这样给，CSP 不允许外链）。"""
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def inline_image(data: bytes, name: str) -> str | None:
    """图片转 ``data:`` URI；类型不认识或太大就返回 ``None``。"""
    mime = guess_image_mime(name)
    if mime is None or not data or len(data) > MAX_INLINE_IMAGE_BYTES:
        return None
    return data_uri(data, mime)


__all__ = [
    "ALLOWED_PROTOCOLS",
    "CONTENT_ATTRIBUTES",
    "CONTENT_TAGS",
    "IMAGE_MIME_TYPES",
    "MAX_INLINE_IMAGE_BYTES",
    "clean_html",
    "data_uri",
    "drop_dangerous_blocks",
    "guess_image_mime",
    "inline_image",
    "strip_tags",
]
