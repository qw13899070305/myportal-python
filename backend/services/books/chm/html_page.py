"""单个主题页的加工：取正文 → 内联图片 → 改写链接 → 交给共用清洗。

产出的是"可以塞进任何 WebView 的安全片段"，不含外壳、CSS、按钮文案；
``<style>`` 块由 :mod:`backend.services.books.sanitize` 整段丢弃（帮助页的
CSS 常常会给整页做绝对定位，留着反而会盖住宿主界面）。
"""

from __future__ import annotations

import html as html_lib
import posixpath
import re
from typing import TYPE_CHECKING
from urllib.parse import unquote

from backend.services.books.sanitize import (
    MAX_INLINE_IMAGE_BYTES,
    clean_html,
    inline_image,
    strip_tags,
)

from .textutil import strip_chm_prefix

if TYPE_CHECKING:  # pragma: no cover - 只为类型标注
    from .container import ChmFile

#: 标签 / 属性解析（.hhc 解析也复用这两个正则）
TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:[^>\"']|\"[^\"]*\"|'[^']*')*?)(/?)>", re.S)
ATTR_RE = re.compile(r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*("[^"]*"|'[^']*'|[^\s"'>]+)""")

_BODY_RE = re.compile(r"<body\b[^>]*>(.*?)(?:</body\s*>|$)", re.I | re.S)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title\s*>", re.I | re.S)
_SPACE_RE = re.compile(r"\s+")
#: 判断一段字节解出来是不是网页（有些 .htm 其实是二进制/文本杂项）
_HTML_HINT_RE = re.compile(
    r"<\s*(?:!doctype|html|body|head|h[1-6]|p|div|table|span|a|font|br)\b", re.I
)

#: 会被整段删掉的头部标签（其余危险标签由共用清洗负责）
_HEAD_TAGS = ("title", "meta", "link", "base", "xml")

#: 会被改写的标签
_URL_TAGS = ("a", "area", "img")

#: 默认允许内联的图片总量（单张上限来自共用清洗模块）
DEFAULT_MAX_IMAGE_BYTES_TOTAL = 6 * 1024 * 1024


def parse_attrs(source: str) -> dict[str, str]:
    """把标签里的属性解析成 dict（重复取第一个，大小写不敏感）。"""
    attrs: dict[str, str] = {}
    for match in ATTR_RE.finditer(source or ""):
        key = match.group(1).lower()
        value = match.group(2)
        if value[:1] in ("'", '"'):
            value = value[1:-1]
        attrs.setdefault(key, value)
    return attrs


def extract_title(text: str) -> str:
    """取 ``<title>`` 作为章节标题（取不到返回空串）。"""
    match = _TITLE_RE.search(text or "")
    if not match:
        return ""
    title = _SPACE_RE.sub(" ", html_lib.unescape(match.group(1))).strip()
    return title[:200]


def looks_like_html(text: str) -> bool:
    """粗略判断一段解码后的文本是不是网页正文。"""
    return bool(_HTML_HINT_RE.search((text or "")[:2048]))


class PageBuilder:
    """把一个主题页加工成安全片段。

    ``anchors`` 是"内部路径(小写) -> 章节锚点"，用来把站内链接改成页内锚点；
    图片内联的总量预算记在实例上，一本书共用一个实例即可。
    """

    def __init__(
        self,
        chm: ChmFile,
        anchors: dict[str, str],
        *,
        max_image_bytes: int = MAX_INLINE_IMAGE_BYTES,
        max_images_total: int = DEFAULT_MAX_IMAGE_BYTES_TOTAL,
    ) -> None:
        self._chm = chm
        self._anchors = anchors
        self._max_image_bytes = max_image_bytes
        self._max_images_total = max_images_total
        self._images_total = 0

    # ---------------- 对外 ----------------

    def build(self, topic: str, text: str) -> str:
        """返回清洗过的正文片段（``text`` 是原始 HTML 文本）。"""
        text = self._strip_head(text)
        body = _BODY_RE.search(text)
        if body:
            text = body.group(1)
        text = self._rewrite_tags(topic, text)
        return clean_html(text)

    def chapter_text(self, fragment: str) -> str:
        """正文片段的纯文本（Book.Chapter.text）。"""
        return strip_tags(fragment)

    # ---------------- 头部与标签 ----------------

    @staticmethod
    def _strip_head(text: str) -> str:
        """删掉 <title>/<meta>/<link>/<base>：它们不是正文，文字留下来会串味。"""
        for tag in _HEAD_TAGS:
            text = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}\s*>", " ", text, flags=re.I | re.S)
            text = re.sub(rf"<{tag}\b[^>]*/?>", " ", text, flags=re.I)
        return text

    def _rewrite_tags(self, topic: str, text: str) -> str:
        out: list[str] = []
        pos = 0
        for match in TAG_RE.finditer(text):
            out.append(text[pos : match.start()])
            pos = match.end()
            out.append(self._rewrite_tag(topic, match))
        out.append(text[pos:])
        return "".join(out)

    def _rewrite_tag(self, topic: str, match: re.Match) -> str:
        closing, name, attrs_src, _ = match.groups()
        tag = name.lower()
        if closing or tag not in _URL_TAGS:
            return match.group(0)
        attrs = parse_attrs(attrs_src)
        if tag == "img":
            return self._rewrite_img(topic, attrs)
        href = attrs.get("href", "")
        if not href:
            return match.group(0)
        attrs["href"] = self._rewrite_href(topic, href)
        rendered = "".join(
            f" {key}='{html_lib.escape(value, quote=True)}'" for key, value in attrs.items() if value
        )
        return f"<{tag}{rendered}>"

    def _rewrite_img(self, topic: str, attrs: dict[str, str]) -> str:
        data_uri = self._inline_image(topic, attrs.get("src", ""))
        if data_uri is None:
            # 找不到 / 太大 / 类型不支持：图片本身丢掉，保留文档自带的 alt 文字
            alt = (attrs.get("alt") or "").strip()
            if not alt:
                return ""
            return f"<span class='chm-image-missing'>{html_lib.escape(alt[:100])}</span>"
        rest = "".join(
            f" {key}='{html_lib.escape(value, quote=True)}'"
            for key, value in attrs.items()
            if key in ("alt", "title", "width", "height") and value
        )
        return f"<img src='{data_uri}'{rest}>"

    # ---------------- 链接 ----------------

    def _rewrite_href(self, topic: str, href: str) -> str:
        """外部 http(s) 保留；页内锚点保留；站内路径改成页内锚点或 ``#``。"""
        value = strip_chm_prefix(href)
        low = value.lower()
        if not value:
            return "#"
        if low.startswith(("http://", "https://", "mailto:")):
            return value
        if low.startswith(
            ("javascript:", "vbscript:", "data:", "file:", "about:", "ms-its:", "mk:", "res:")
        ):
            return "#"
        if value.startswith("#"):
            return value
        path, _, _fragment = value.partition("#")
        target = self._resolve_path(topic, path)
        anchor = self._anchors.get(target.lower()) if target else None
        return f"#{anchor}" if anchor else "#"

    def _resolve_path(self, topic: str, ref: str) -> str | None:
        ref = unquote(strip_chm_prefix(ref).replace("\\", "/")).split("?", 1)[0]
        if not ref:
            return None
        candidates = []
        if ref.startswith("/"):
            candidates.append(ref.lstrip("/"))
        else:
            base = posixpath.dirname(topic)
            candidates.append(
                (posixpath.normpath(posixpath.join(base, ref)) if base else ref).lstrip("/")
            )
            candidates.append(ref)
        for candidate in candidates:
            found = self._chm.find(candidate)
            if found:
                return found
        return None

    def _inline_image(self, topic: str, src: str) -> str | None:
        """CHM 内部图片 -> ``data:`` URI；外链、找不到、超预算都返回 None。"""
        if not src or src.lower().startswith(("http://", "https://", "data:")):
            return None
        path = self._resolve_path(topic, src)
        if not path:
            return None
        size = self._chm.size(path)
        if size <= 0 or size > self._max_image_bytes:
            return None
        if self._images_total + size > self._max_images_total:
            return None
        raw = self._chm.read(path)
        if not raw:
            return None
        uri = inline_image(raw, path)
        if uri is None:
            return None
        self._images_total += len(raw)
        return uri


__all__ = ["PageBuilder", "extract_title", "looks_like_html", "parse_attrs"]
