"""章节正文：一章 XHTML → :class:`Chapter`。

做四件事，一件都不涉及页面外壳：

1. 标题取章内第一个 ``h1``~``h3``（取不到就用文件名），并从正文里摘掉，
   免得客户端再画一遍标题时重复
2. 链接重写：指向本书别的章节的 → ``#锚点``；``javascript:`` 一律丢掉；
   外链默认也只留文字（原地址写进 ``title``，见 :data:`KEEP_EXTERNAL_LINKS`）
3. 图片交给 :mod:`.assets` 内联成 ``data:`` URI，内联不了的留一句占位说明
4. 正文交给 :func:`backend.services.books.sanitize.clean_html` 统一清洗

正文里的 ``id`` 与 ``a[name]`` 都不保留——锚点只由客户端按
``Chapter.anchor`` 生成，否则书里同名的老锚点会把目录跳转抢走。

XHTML 畸形到解析不了时退回"整段清洗"：正文照常出来，但不再重写链接、也不
内联图片（图片留占位），避免客户端去请求根本不存在的相对路径。
"""

from __future__ import annotations

import posixpath
import re
from html import escape as escape_html
from urllib.parse import urlsplit
from xml.etree import ElementTree

from backend.services.books.model import Chapter
from backend.services.books.sanitize import clean_html, strip_tags

from .assets import InlineBudget, inline_source
from .container import EpubContainer, book_path
from .xmlutil import (
    child_parent_map,
    decode_bytes,
    drop_subtrees,
    element_text,
    find_all,
    find_first,
    parse_xhtml,
    strip_namespaces,
)

#: 是否保留指向外部网站的可点击链接。预览在 iframe 里，点出去就"跑出书"了，
#: 所以默认只把原地址写进 ``title``；哪天想放开，改成 ``True`` 即可。
KEEP_EXTERNAL_LINKS = False

#: 外部协议（保不保留由 :data:`KEEP_EXTERNAL_LINKS` 决定，别的协议一律丢掉）
_EXTERNAL_SCHEMES = frozenset({"http", "https", "mailto", "ftp", "tel"})
#: 章节标题优先取这些标签
_HEADING_TAGS = ("h1", "h2", "h3")
#: 整棵丢掉 ``head``：共用清洗器不管它，而正文里也不该有它
#: （script / style / iframe / object 等由 ``clean_html`` 统一负责，这里不重复一份名单）
_DROP_TAGS = frozenset({"head"})
#: 图片内联失败时的占位说明用的 class（内容级提示，不是页面文案）
IMAGE_NOTE_CLASS = "book-img-note"

_HEADING_RE = re.compile(r"(?is)<h([1-3])\b[^>]*>(.*?)</h\1\s*>")
_HREF_ATTR_RE = re.compile(r"""(?i)\shref\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""")
_NAME_ATTR_RE = re.compile(r"""(?i)\sname\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""")
_IMG_TAG_RE = re.compile(r"(?is)<img\b[^>]*>")
_ALT_ATTR_RE = re.compile(r"""(?i)\balt\s*=\s*("[^"]*"|'[^']*')""")
_TAG_RE = re.compile(r"(?s)<[^>]*>")
_BODY_RE = re.compile(r"(?is)<body\b[^>]*>(.*?)</body\s*>")
_HEAD_BLOCK_RE = re.compile(r"(?is)<head\b[^>]*>.*?</head\s*>")
_CONTROL_RE = re.compile(r"[\x00-\x20\x7f]+")


def parse_chapter(
    container: EpubContainer,
    path: str,
    *,
    index: int,
    anchors: dict[str, str],
    budget: InlineBudget,
) -> Chapter | None:
    """渲染一章；条目读不出来（文件缺失 / 被加密）返回 ``None``，由调用方跳过。"""
    raw = container.read(path)
    if raw is None:
        return None
    text = decode_bytes(raw)
    root = parse_xhtml(text)
    if root is None:
        title, html = _render_loose(path, text)
    else:
        title, html = _render_tree(container, path, root, anchors, budget)
    return Chapter(
        index=index,
        title=title,
        html=html,
        text=strip_tags(html),
        anchor=anchors.get(path) or f"epub-{index}",
    )


# ---------------- 正常路径：能解析成树 ----------------


def _render_tree(
    container: EpubContainer,
    path: str,
    root: ElementTree.Element,
    anchors: dict[str, str],
    budget: InlineBudget,
) -> tuple[str, str]:
    """XHTML 解析得动时的正路：在树上重写链接与图片，最后统一清洗。"""
    strip_namespaces(root)
    drop_subtrees(root, _DROP_TAGS)
    body = find_first(root, "body")
    if body is None:
        body = root
    parents = child_parent_map(body)
    title = _take_heading(body, parents) or posixpath.basename(path)
    _rewrite_links(container, body, path, anchors)
    _rewrite_images(container, body, parents, path, budget)
    html = "".join(
        ElementTree.tostring(child, encoding="unicode", method="html") for child in body
    )
    return title, clean_html(html)


def _take_heading(body: ElementTree.Element, parents: dict) -> str:
    """取章内第一个 ``h1``~``h3`` 当标题，并把它从正文里摘掉。"""
    for elem in body.iter():
        if elem.tag not in _HEADING_TAGS:
            continue
        title = element_text(elem)
        parent = parents.get(elem)
        if parent is None:
            return title
        position = list(parent).index(elem)
        tail = elem.tail or ""
        parent.remove(elem)
        if tail.strip():  # 标题后面的文字别丢
            previous = parent[position - 1] if position else None
            if previous is not None:
                previous.tail = (previous.tail or "") + tail
            else:
                parent.text = (parent.text or "") + tail
        return title
    return ""


def _rewrite_links(
    container: EpubContainer,
    body: ElementTree.Element,
    chapter_path: str,
    anchors: dict[str, str],
) -> None:
    """书内链接 → ``#锚点``；外链按开关处理；其余（``javascript:`` 等）去掉 href。"""
    for link in find_all(body, "a"):
        link.attrib.pop("name", None)  # 锚点只由客户端生成，书里的 name 不参与
        original = (link.get("href") or "").strip()
        target = (
            _link_target(container, original, chapter_path, anchors) if original else None
        )
        if target:
            link.set("href", target)
            continue
        link.attrib.pop("href", None)
        # 外链留个"原地址"在 title 里（javascript: / data: 这类不回显）
        if original and _is_showable(original) and not link.get("title"):
            link.set("title", original)


def _link_target(
    container: EpubContainer,
    href: str,
    chapter_path: str,
    anchors: dict[str, str],
) -> str | None:
    """算出该写进 ``href`` 的值；``None`` 表示这个链接不该可点。"""
    raw = href.strip()
    if not raw:
        return None
    # 先去掉空白与控制字符再判断协议，挡住 "java\tscript:" 这类花招
    scheme = urlsplit(_CONTROL_RE.sub("", raw)).scheme.lower()
    if scheme:
        return raw if (scheme in _EXTERNAL_SCHEMES and KEEP_EXTERNAL_LINKS) else None
    file_part = raw.split("#", 1)[0].split("?", 1)[0]
    if not file_part:
        return _anchor_href(anchors, chapter_path)  # 纯锚点 #fn1 → 折叠到本章开头
    resolved = container.resolve(book_path(chapter_path, file_part))
    return _anchor_href(anchors, resolved) if resolved else None


def _anchor_href(anchors: dict[str, str], path: str | None) -> str | None:
    anchor = anchors.get(path) if path else None
    return f"#{anchor}" if anchor else None


def _is_showable(href: str) -> bool:
    """丢掉 href 之后，这个地址还值不值得写进 ``title`` 留个出处。"""
    scheme = urlsplit(_CONTROL_RE.sub("", href)).scheme.lower()
    return scheme in _EXTERNAL_SCHEMES or not scheme


def _rewrite_images(
    container: EpubContainer,
    body: ElementTree.Element,
    parents: dict,
    chapter_path: str,
    budget: InlineBudget,
) -> None:
    """能内联的图片换成 ``data:`` URI，其余换成占位说明。"""
    for img in list(find_all(body, "img")):
        src = (img.get("src") or "").strip()
        data_uri = inline_source(container, src, chapter_path, budget)
        if data_uri:
            img.set("src", data_uri)
            img.attrib.pop("srcset", None)
            continue
        label = (img.get("alt") or "").strip() or posixpath.basename(src) or "图片"
        placeholder = ElementTree.Element("span", {"class": IMAGE_NOTE_CLASS})
        placeholder.text = f"[图片未内联：{label}]"
        parent = parents.get(img)
        if parent is None:
            img.attrib.pop("src", None)  # 兜底：别让客户端去请求相对路径
        else:
            parent[list(parent).index(img)] = placeholder


# ---------------- 退路：XHTML 畸形 ----------------


def _render_loose(path: str, text: str) -> tuple[str, str]:
    """解析不了树时的退路：整段交给共用清洗器，链接 / 图片做最保守的处理。"""
    html = _body_slice(text)
    title, html = _loose_title(html, path)
    html = _HREF_ATTR_RE.sub("", html)  # 没有 DOM 可用，href 一律不留
    html = _NAME_ATTR_RE.sub("", html)  # a[name] 同理，锚点只由客户端生成
    return title, clean_html(_IMG_TAG_RE.sub(_img_placeholder, html))


def _body_slice(text: str) -> str:
    """能取到 ``<body>`` 就只取它——顺便把 ``<head>`` 里的 title/style 挡掉。"""
    match = _BODY_RE.search(text)
    if match:
        return match.group(1)
    return _HEAD_BLOCK_RE.sub(" ", text)


def _loose_title(html: str, path: str) -> tuple[str, str]:
    """从畸形章节里抠出标题（第一个 ``h1``~``h3``），并把它从正文里剪掉。"""
    fallback = posixpath.basename(path)
    match = _HEADING_RE.search(html)
    if match is None:
        return fallback, html
    title = " ".join(_TAG_RE.sub("", match.group(2)).split())
    return (title or fallback), html[: match.start()] + html[match.end() :]


def _img_placeholder(match: re.Match) -> str:
    alt = _ALT_ATTR_RE.search(match.group(0))
    label = alt.group(1).strip("\"'").strip() if alt else ""
    return _image_note(label or "图片")


def _image_note(label: str) -> str:
    return f'<span class="{IMAGE_NOTE_CLASS}">[图片未内联：{escape_html(label)}]</span>'


__all__ = ["IMAGE_NOTE_CLASS", "KEEP_EXTERNAL_LINKS", "parse_chapter"]
