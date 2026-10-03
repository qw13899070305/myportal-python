"""CHM 里的文本编码与链接前缀（纯函数，与容器结构无关）。

CHM 的正文编码没有统一规定：可能带 BOM、可能在 ``<meta charset>`` 里声明、
也可能只能按 ITSF 头里的 LCID 猜；帮助页里的链接又常写成
``mk:@MSITStore:foo.chm::/bar.htm``，都要在这里归一化。
"""

from __future__ import annotations

import re

#: 少数常见语言的 ANSI 代码页（按 ITSF 头里的 LCID 取）
CODEPAGE_BY_LCID: dict[int, str] = {
    0x0404: "cp950",
    0x0405: "cp1250",
    0x0406: "cp1252",
    0x0407: "cp1252",
    0x0408: "cp1253",
    0x0409: "cp1252",
    0x040A: "cp1252",
    0x040B: "cp1252",
    0x040C: "cp1252",
    0x040D: "cp1255",
    0x040E: "cp1250",
    0x040F: "cp1252",
    0x0410: "cp1252",
    0x0411: "cp932",
    0x0412: "cp949",
    0x0413: "cp1252",
    0x0414: "cp1252",
    0x0415: "cp1250",
    0x0416: "cp1252",
    0x0419: "cp1251",
    0x041D: "cp1252",
    0x041F: "cp1254",
    0x0422: "cp1251",
    0x0424: "cp1250",
    0x0804: "cp936",
    0x0809: "cp1252",
}

#: LCID -> 语言标签（给 Book.language 用，够用就行）
LANGUAGE_BY_LCID: dict[int, str] = {
    0x0404: "zh-TW",
    0x0405: "cs",
    0x0406: "da",
    0x0407: "de",
    0x0408: "el",
    0x0409: "en-US",
    0x040A: "es",
    0x040B: "fi",
    0x040C: "fr",
    0x040E: "hu",
    0x040F: "is",
    0x0410: "it",
    0x0411: "ja",
    0x0412: "ko",
    0x0413: "nl",
    0x0414: "no",
    0x0415: "pl",
    0x0416: "pt-BR",
    0x0419: "ru",
    0x041D: "sv",
    0x041F: "tr",
    0x0422: "uk",
    0x0804: "zh-CN",
    0x0809: "en-GB",
}

_CHARSET_RE = re.compile(rb"""charset\s*=\s*["']?\s*([A-Za-z0-9_\-]+)""", re.I)
#: 帮助页里的链接常写成 mk:@MSITStore:foo.chm::/bar.htm / ms-its:foo.chm::/bar.htm
_CHM_URL_PREFIX_RE = re.compile(r"^\s*(?:mk:@msitstore|ms-its|ms-help):[^:]*::", re.I)


def strip_chm_prefix(ref: str) -> str:
    """去掉 ``mk:@MSITStore:x.chm::`` 之类的前缀，留下 CHM 内部路径。"""
    return _CHM_URL_PREFIX_RE.sub("", (ref or "").strip())


def language_tag(lcid: int) -> str:
    """LCID -> 语言标签；不认识就退回 ``0x0409`` 这种十六进制写法。"""
    return LANGUAGE_BY_LCID.get(lcid & 0xFFFF, f"0x{lcid & 0xFFFF:04x}")


def decode_text(raw: bytes, lcid: int = 0) -> str:
    """按 BOM / meta charset / LCID 的顺序猜正文编码。"""
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8", "replace")
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", "replace")
    match = _CHARSET_RE.search(raw[:4096])
    if match:
        encoding = match.group(1).decode("ascii", "replace").lower()
        try:
            return raw.decode(encoding, "replace")
        except LookupError:
            pass
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    return raw.decode(CODEPAGE_BY_LCID.get(lcid & 0xFFFF, "cp1252"), "replace")


def decode_system_string(raw: bytes) -> str:
    """``/#SYSTEM`` 里的字符串：UTF-16LE 与 ANSI 混用，按内容猜。"""
    if not raw:
        return ""
    if (
        len(raw) % 2 == 0
        and raw[1::2].count(0) == len(raw) // 2
        and raw[0::2].count(0) < len(raw) // 2
    ):
        return raw.decode("utf-16le", "replace").rstrip("\x00")
    for encoding in ("utf-8", "cp1252"):
        try:
            return raw.decode(encoding).rstrip("\x00")
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1").rstrip("\x00")


__all__ = [
    "CODEPAGE_BY_LCID",
    "LANGUAGE_BY_LCID",
    "decode_system_string",
    "decode_text",
    "language_tag",
    "strip_chm_prefix",
]
