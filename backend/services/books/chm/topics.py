"""主题页与目录树：默认主题、.hhc/.hhk 目录、正文页面筛选排序。

只处理"有哪些页面、顺序如何、标题叫什么"，不管页面内容长什么样
（内容加工在 :mod:`~backend.services.books.chm.html_page`）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .html_page import TAG_RE, parse_attrs
from .textutil import decode_text, strip_chm_prefix

if TYPE_CHECKING:  # pragma: no cover - 只为类型标注
    from .container import ChmFile

#: 视为"正文页面"的扩展名
HTML_EXTENSIONS = (".htm", ".html", ".xhtml", ".xht")

#: /#SYSTEM 里几个用得上的条目编号
SYSTEM_CONTENTS_FILE = 0x0000
SYSTEM_DEFAULT_TOPIC = 0x0002
SYSTEM_TITLE = 0x0003

#: .hhc/.hhk 里这条 <param> 的 name 取值 -> 我们关心的字段
_PARAM_KEYS = ("name", "local", "keyword")


@dataclass
class TocItem:
    """目录树里的一个条目；``path`` 是解析到的真实内部路径（可能为空）。"""

    level: int
    title: str
    target: str
    path: str | None = None


def html_files(chm: ChmFile) -> list[str]:
    """全部正文页面，按路径排序（做兜底目录用）。"""
    return sorted(
        (name for name in chm.names() if name.lower().endswith(HTML_EXTENSIONS)),
        key=lambda name: name.lower(),
    )


def book_title(chm: ChmFile) -> str:
    """CHM 标题（SYSTEM 0x0003）。"""
    return chm.system_string(SYSTEM_TITLE)


def default_topic(chm: ChmFile) -> str | None:
    """默认主题（SYSTEM 0x0002），解析不到返回 ``None``。"""
    name = chm.system_string(SYSTEM_DEFAULT_TOPIC)
    return chm.find(name) if name else None


def contents_file(chm: ChmFile) -> str | None:
    """目录文件（SYSTEM 0x0000，通常是 .hhc）。"""
    name = chm.system_string(SYSTEM_CONTENTS_FILE)
    return chm.find(name) if name else None


def parse_hhc(text: str, limit: int) -> list[TocItem]:
    """解析 .hhc/.hhk（HTML 形式的目录树）。

    只看 ``<ul>`` / ``<li>`` / ``<param name="Name|Local" value="...">``，
    所以对残缺标签也有一定容错。``level`` 是最外层 ``<ul>`` 内的层级（从 0 起）。
    """
    items: list[TocItem] = []
    depth = 0
    pending: dict[str, str] = {}

    def flush() -> None:
        title = (pending.get("name") or "").strip()
        target = (pending.get("local") or "").strip()
        if title or target:
            items.append(TocItem(max(0, depth - 1), title or target, target))
        pending.clear()

    for match in TAG_RE.finditer(text):
        closing, name, attrs_src, _ = match.groups()
        tag = name.lower()
        if tag == "ul":
            if closing:
                flush()
                depth = max(0, depth - 1)
            else:
                depth += 1
        elif tag == "li":
            flush()
        elif tag == "param" and not closing:
            attrs = parse_attrs(attrs_src)
            key = attrs.get("name", "").strip().lower()
            if key in _PARAM_KEYS:
                pending[key] = attrs.get("value", "")
        elif tag == "object" and closing:
            flush()
        if len(items) >= limit:
            break
    flush()
    return items[:limit]


def _resolve_target(chm: ChmFile, target: str) -> str | None:
    """目录条目的 Local -> 真实正文路径（不指向网页就返回 None）。"""
    ref = strip_chm_prefix(target or "").split("#", 1)[0].strip().replace("\\", "/")
    if not ref or ":" in ref.split("/")[0]:
        return None
    path = chm.find(ref)
    if path and path.lower().endswith(HTML_EXTENSIONS):
        return path
    return None


def build_toc(chm: ChmFile, limit: int) -> tuple[list[TocItem], bool]:
    """目录树：优先 .hhc（SYSTEM 指定的，其次文件里任意一个），否则退化成全部页面。

    返回 ``(条目, 是否因为超限被截断)``。
    """
    candidates: list[str] = []
    contents = contents_file(chm)
    if contents:
        candidates.append(contents)
    candidates.extend(
        name
        for name in chm.names()
        if name.lower().endswith((".hhc", ".hhk")) and name not in candidates
    )
    for name in candidates:
        raw = chm.read(name)
        if not raw:
            continue
        items = parse_hhc(decode_text(raw, chm.language), limit + 1)
        for item in items:
            item.path = _resolve_target(chm, item.target)
        if items:
            return items[:limit], len(items) > limit

    files = html_files(chm)
    items = [TocItem(0, name, name, name) for name in files[:limit]]
    return items, len(files) > limit


def topic_order(chm: ChmFile, items: list[TocItem], default: str | None) -> list[str]:
    """渲染顺序：默认主题 → 目录顺序 → 其余正文页面按路径排序。"""
    order: list[str] = []
    seen: set[str] = set()

    def push(name: str | None) -> None:
        if not name:
            return
        key = name.lower()
        if key in seen:
            return
        seen.add(key)
        order.append(name)

    push(default)
    for item in items:
        push(item.path)
    for name in html_files(chm):
        push(name)
    return order


def toc_titles(items: list[TocItem]) -> dict[str, str]:
    """路径 -> 目录里的标题（给正文页取不到 ``<title>`` 时兜底）。"""
    titles: dict[str, str] = {}
    for item in items:
        if item.path and item.title:
            titles.setdefault(item.path.lower(), item.title)
    return titles


__all__ = [
    "HTML_EXTENSIONS",
    "TocItem",
    "book_title",
    "build_toc",
    "contents_file",
    "default_topic",
    "html_files",
    "parse_hhc",
    "toc_titles",
    "topic_order",
]
