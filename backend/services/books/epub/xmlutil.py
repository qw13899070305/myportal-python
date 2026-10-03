"""EPUB 解析用到的 XML / XHTML 小工具。

EPUB 的正文名义上是 XML，实际上经常畸形：``&nbsp;`` 没声明、``<br>`` 没
自闭合、``<p>`` 不闭合、注释里夹着走私标签……脏活都集中在这里：

- :func:`parse_xml` / :func:`parse_xhtml`：宽容解析（实在解析不了返回 ``None``）
- :func:`strip_namespaces` / :func:`find_first` / :func:`find_all` /
  :func:`drop_subtrees` / :func:`child_parent_map` / :func:`element_text`
- :func:`decode_bytes`：按文件自己声明的编码解码

全是纯函数：不认识"书"，也不认识"页面"。
"""

from __future__ import annotations

import re
from html.entities import html5 as _HTML5_ENTITIES
from xml.etree import ElementTree

#: XML 声明里的编码（不少中文电子书还是 gbk / big5）
_ENCODING_RE = re.compile(rb"""encoding\s*=\s*["']([\w.:-]+)["']""", re.I)
#: HTML 命名实体（``&nbsp;`` 这类 XML 解析器不认，先换成数字引用）
_ENTITY_RE = re.compile(r"&([A-Za-z][A-Za-z0-9]{1,31});")
#: 没自闭合的空标签——XHTML 里非法，但真实电子书里到处都是
_VOID_TAG_RE = re.compile(
    r"<(br|hr|img|meta|link|input|col|area|base|source|track|wbr)"
    r"((?:\s[^<>]*?)?)(?<!/)>",
    re.I | re.S,
)


def localname(tag: object) -> str:
    """``{namespace}Tag`` → ``tag``（小写）；注释 / 处理指令返回空串。"""
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1].lower()


def strip_namespaces(root: ElementTree.Element) -> None:
    """就地去掉命名空间、属性前缀与注释，后面就能按裸标签名（小写）处理。"""
    for parent in list(root.iter()):
        for child in list(parent):
            if not isinstance(child.tag, str):
                parent.remove(child)  # 注释 / 处理指令
    for elem in list(root.iter()):
        if not isinstance(elem.tag, str):
            continue
        elem.tag = localname(elem.tag)
        for key in list(elem.attrib):
            local = localname(key)
            if local and local != key:
                elem.attrib[local] = elem.attrib.pop(key)


def find_first(root: ElementTree.Element, name: str) -> ElementTree.Element | None:
    """按裸标签名找第一个后代（含自身）。"""
    for elem in root.iter():
        if elem.tag == name:
            return elem
    return None


def find_all(root: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    """按裸标签名找全部后代。"""
    return [elem for elem in root.iter() if elem.tag == name]


def drop_subtrees(root: ElementTree.Element, names: frozenset[str] | set[str]) -> None:
    """整棵删掉指定标签（连同其中的文本）。"""
    for parent in list(root.iter()):
        for child in list(parent):
            if isinstance(child.tag, str) and child.tag in names:
                parent.remove(child)


def child_parent_map(root: ElementTree.Element) -> dict:
    """子 → 父 的映射（ElementTree 没有 getparent，替换节点时要用）。"""
    return {child: parent for parent in root.iter() for child in parent}


def element_text(elem: ElementTree.Element | None) -> str:
    """取元素里的纯文本，连续空白压成一个空格。"""
    if elem is None:
        return ""
    return " ".join("".join(elem.itertext()).split())


def decode_bytes(raw: bytes) -> str:
    """尽量按文件自己声明的编码解码，失败再退回 UTF-8 + 替换字符。"""
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", "replace")
    match = _ENCODING_RE.search(raw[:200])
    codecs: list[str] = []
    if match:
        codecs.append(match.group(1).decode("ascii", "ignore"))
    codecs.append("utf-8")
    for codec in codecs:
        try:
            return raw.decode(codec)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", "replace")


def parse_xml(raw: bytes | None) -> ElementTree.Element | None:
    """严格按 XML 解析字节（container.xml / OPF 用）；解析不了返回 ``None``。"""
    if not raw:
        return None
    try:
        return ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        return None


def normalize_entities(text: str) -> str:
    """把 HTML 命名实体换成数字引用：``&nbsp;`` 这类 XML 解析器不认。"""

    def replace(match: re.Match) -> str:
        char = _HTML5_ENTITIES.get(match.group(1) + ";")
        if not char:
            return match.group(0)
        return "".join(f"&#{ord(item)};" for item in char)

    return _ENTITY_RE.sub(replace, text)


def selfclose_void_tags(text: str) -> str:
    """给 ``<br>`` / ``<img ...>`` 补上自闭合斜杠，XHTML 才解析得动。"""
    return _VOID_TAG_RE.sub(lambda m: f"<{m.group(1)}{m.group(2)}/>", text)


def parse_xhtml(text: str) -> ElementTree.Element | None:
    """宽容地把章节 XHTML 解析成 ElementTree，实在不行返回 ``None``。

    先做两件常见修补（命名实体、空标签自闭合）再交给 XML 解析器；
    仍然失败说明这一章畸形得比较厉害，由调用方决定怎么降级。
    """
    fixed = selfclose_void_tags(normalize_entities(text))
    for candidate in (fixed, text):
        try:
            return ElementTree.fromstring(candidate)
        except ElementTree.ParseError:
            continue
    return None


__all__ = [
    "child_parent_map",
    "decode_bytes",
    "drop_subtrees",
    "element_text",
    "find_all",
    "find_first",
    "localname",
    "normalize_entities",
    "parse_xhtml",
    "parse_xml",
    "selfclose_void_tags",
    "strip_namespaces",
]
