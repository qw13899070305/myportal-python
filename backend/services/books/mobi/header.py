"""MOBI 头部结构：PalmDOC 头 / MOBI 头 / EXTH / KF8 分段。

字段偏移以 MobileRead 的 MOBI 格式页为准：

- PalmDOC 头：记录开头 16 字节（compression / text_length / record_count / …）
- MOBI 头：紧跟 PalmDOC 头，内部偏移**相对 "MOBI" 魔数**，
  0x40 first_non_book_index、0x44/0x48 全名偏移与长度、0x5C 首个图片记录、
  0x60..0x6C HUFF/CDIC 表位置、0x70 EXTH 标志、0x98/0x9C DRM、0xB0/0xB2
  正文首尾记录、0xE0 正文记录末尾的额外数据标志
- EXTH：MOBI 头之后（``exth_flags & 0x40``），type 100 作者、503 更新书名、524 语言
- KF8 双段文件：BOUNDARY 记录 +16 字节处是第二段（KF8）的 PalmDOC + MOBI 头，
  正文从 BOUNDARY 的下一条记录开始
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.services.books.mobi.errors import MobiFormatError
from backend.services.books.mobi.pdb import PalmDatabase, Reader

#: PalmDOC 头长度
PALMDOC_HEADER_SIZE = 16
#: MOBI 头的魔数
MOBI_MAGIC = b"MOBI"
#: KF8 分界记录的魔数
BOUNDARY_MAGIC = b"BOUNDARY"
#: compression = 17480 表示 HUFF/CDIC
HUFF_COMPRESSION = 17480
#: text_encoding -> Python 编码名
ENCODINGS = {1252: "cp1252", 65001: "utf-8"}
#: 无 DRM 时 DRM 偏移/数量字段的取值（规范写 0xFFFFFFFF，实测也有 0）
ABSENT = (0, 0xFFFFFFFF)
#: 正文记录末尾额外数据的标志位：0x01 多字节、0x02 TBS、0x04 不可断行
TRAILING_DATA_MASK = 0x07
#: EXTH 里我们关心的几个 type
EXTH_AUTHOR = 100
EXTH_UPDATED_TITLE = 503
EXTH_LANGUAGE = 524


@dataclass(frozen=True)
class PalmDocHeader:
    """记录 0 开头的 16 字节 PalmDOC 头。"""

    compression: int
    text_length: int
    record_count: int
    record_size: int
    encryption: int


@dataclass(frozen=True)
class MobiHeader:
    """MOBI 头里的常用字段（偏移相对 "MOBI" 魔数）。"""

    header_length: int
    mobi_type: int
    text_encoding: int
    file_version: int
    first_non_book_index: int
    full_name_offset: int
    full_name_length: int
    first_image_index: int
    huffman_record_offset: int
    huffman_record_count: int
    huffman_table_offset: int
    huffman_table_length: int
    exth_flags: int
    drm_offset: int
    drm_count: int
    extra_data_flags: int

    @property
    def has_exth(self) -> bool:
        return bool(self.exth_flags & 0x40)

    @property
    def has_drm(self) -> bool:
        return self.drm_offset not in ABSENT or self.drm_count not in ABSENT

    @property
    def is_kf8(self) -> bool:
        # 单段 KF8（Gutenberg 的 azw3 就是这种）没有 BOUNDARY，只能看版本号
        return self.file_version >= 8 or self.mobi_type == 248


@dataclass
class Section:
    """一段 MOBI 数据（KF8 双段文件里有两段，各自带一套头）。"""

    palmdoc: PalmDocHeader
    mobi: MobiHeader | None
    exth: dict[int, list[bytes]]
    #: 正文首条记录号（记录 0 那段从 1 开始；KF8 段从 BOUNDARY 的下一条开始）
    text_start: int
    encoding: str
    title: str = ""
    author: str = ""
    language: str = ""
    #: KF8 段的图片记录号可能相对本段起算，用它再试一次
    image_bias: int = 0

    @property
    def is_kf8(self) -> bool:
        return self.mobi is not None and self.mobi.is_kf8

    @property
    def has_drm(self) -> bool:
        return self.palmdoc.encryption != 0 or (self.mobi is not None and self.mobi.has_drm)


# ---------------- 头部解析 ----------------


def parse_mobi_header(reader: Reader, start: int) -> MobiHeader:
    """解析 MOBI 头，``start`` 是 "MOBI" 魔数的偏移。"""
    header_length = reader.u32(start + 4)
    if not 24 <= header_length <= 4096:
        raise MobiFormatError(f"MOBI 头长度异常：{header_length}")

    def field(offset: int, default: int = 0xFFFFFFFF) -> int:
        return reader.u32(start + offset) if reader.has(start + offset, 4) else default

    def short(offset: int, default: int = 0) -> int:
        return reader.u16(start + offset) if reader.has(start + offset, 2) else default

    # 头长小于 228 的文件没有「额外数据标志」这个字段
    extra_flags = field(0xE0, 0) if header_length >= 0xE4 else 0
    return MobiHeader(
        header_length=header_length,
        mobi_type=field(0x08, 0),
        text_encoding=field(0x0C, 0),
        file_version=field(0x14, 0),
        first_non_book_index=field(0x40),
        full_name_offset=field(0x44, 0),
        full_name_length=field(0x48, 0),
        first_image_index=field(0x5C, 0),
        huffman_record_offset=field(0x60, 0),
        huffman_record_count=field(0x64, 0),
        huffman_table_offset=field(0x68, 0),
        huffman_table_length=field(0x6C, 0),
        exth_flags=field(0x70, 0),
        drm_offset=field(0x98),
        drm_count=field(0x9C),
        extra_data_flags=extra_flags,
    )


def parse_exth(reader: Reader, start: int) -> dict[int, list[bytes]]:
    """解析 EXTH（type -> 取值列表）；结构不对就当没有元数据。"""
    if reader.slice(start, 4) != b"EXTH":
        return {}
    length = reader.u32(start + 4)
    count = reader.u32(start + 8)
    if length < 12 or count > 4096:
        raise MobiFormatError(f"EXTH 长度/条目数异常：{length}/{count}")
    records: dict[int, list[bytes]] = {}
    position = start + 12
    end = min(start + length, len(reader.data))
    for _ in range(count):
        if position + 8 > end:
            break
        kind = reader.u32(position)
        size = reader.u32(position + 4)
        if size < 8 or position + size > end:
            break
        records.setdefault(kind, []).append(reader.slice(position + 8, size - 8))
        position += size
    return records


def decode_text(value: bytes, encoding: str) -> str:
    """EXTH / 全名字段的解码：以 NUL 截断，去掉首尾空白。"""
    return value.split(b"\x00", 1)[0].decode(encoding, errors="replace").strip()


def looks_like_name(text: str) -> bool:
    """书名/作者要能看见：允许空格与常见符号，拒绝控制字符与替换符。"""
    return bool(text) and all(char >= " " or char == "\t" for char in text) and "\ufffd" not in text


def _read_full_name(reader: Reader, header: MobiHeader, base: int, encoding: str) -> str:
    """读 MOBI 头里的全名；KF8 段的偏移基准有歧义，两种都试一下。"""
    length = header.full_name_length
    if length <= 0 or length > 1024:
        return ""
    for offset in (header.full_name_offset, base + header.full_name_offset):
        if offset <= 0 or not reader.has(offset, length):
            continue
        name = decode_text(reader.slice(offset, length), encoding)
        if looks_like_name(name):
            return name
    return ""


def parse_section(reader: Reader, base: int, text_start: int) -> Section | None:
    """解析一段 PalmDOC + MOBI 头，``base`` 是 PalmDOC 头在本记录内的偏移。"""
    if not reader.has(base, PALMDOC_HEADER_SIZE):
        return None
    compression = reader.u16(base)
    text_length = reader.u32(base + 4)
    record_count = reader.u16(base + 8)
    record_size = reader.u16(base + 10)
    encryption = reader.u16(base + 12)
    palmdoc = PalmDocHeader(compression, text_length, record_count, record_size, encryption)

    mobi_start = base + PALMDOC_HEADER_SIZE
    header: MobiHeader | None = None
    if reader.has(mobi_start, 4) and reader.slice(mobi_start, 4) == MOBI_MAGIC:
        header = parse_mobi_header(reader, mobi_start)

    encoding = ENCODINGS.get(header.text_encoding if header else 0, "utf-8")
    exth: dict[int, list[bytes]] = {}
    if header is not None and header.has_exth:
        try:
            exth = parse_exth(reader, mobi_start + header.header_length)
        except MobiFormatError:
            exth = {}  # 元数据坏了不影响正文

    section = Section(
        palmdoc=palmdoc,
        mobi=header,
        exth=exth,
        text_start=text_start,
        encoding=encoding,
    )
    if header is not None:
        section.title = _read_full_name(reader, header, base, encoding)
    section.title = _pick_exth(exth, EXTH_UPDATED_TITLE, encoding) or section.title
    section.author = _pick_exth(exth, EXTH_AUTHOR, encoding)
    language = _pick_exth(exth, EXTH_LANGUAGE, encoding)
    section.language = language if len(language) <= 16 and language.isascii() else ""
    return section


def _pick_exth(exth: dict[int, list[bytes]], kind: int, encoding: str) -> str:
    for value in exth.get(kind, []):
        text = decode_text(value, encoding)
        if looks_like_name(text):
            return text
    return ""


# ---------------- 分段（KF8 双段） ----------------


def parse_kf8_section(database: PalmDatabase) -> Section | None:
    """解析 KF8 双段文件里的第二段；结构不对就返回 ``None``（调用方退回前段）。"""
    boundary = database.find_record(BOUNDARY_MAGIC)
    if boundary is None:
        return None
    try:
        section = parse_section(
            Reader(database.record(boundary)), PALMDOC_HEADER_SIZE, boundary + 1
        )
    except MobiFormatError:
        return None
    # 第二段必须是 KF8 头，否则说明这个 BOUNDARY 不是我们认识的布局
    if section is None or section.mobi is None or not section.mobi.is_kf8:
        return None
    section.image_bias = boundary
    if not section.title:
        section.title = database.database_name
    return section


def main_section(database: PalmDatabase) -> Section:
    """记录 0 里的那一段（MOBI 6，或单段 KF8）。"""
    section = parse_section(Reader(database.record(0)), 0, 1)
    if section is None:
        raise MobiFormatError("记录 0 里没有 PalmDOC/MOBI 头")
    if not section.title:
        section.title = database.database_name
    return section


# ---------------- 正文记录末尾的额外数据 ----------------


def trailing_entry_size(record: bytes, end: int) -> int:
    """记录末尾一个额外数据条目的总长度（含长度字节本身）。"""
    result = 0
    shift = 0
    position = end - 1
    while position >= 0:
        value = record[position]
        result |= (value & 0x7F) << shift
        shift += 7
        position -= 1
        if value & 0x80 or shift >= 28:
            return result
    return 0


def strip_trailing_data(record: bytes, flags: int) -> bytes:
    """剥掉正文记录末尾的额外数据。

    这些字节不参与压缩：低位依次是 0x01 跨记录的多字节字符、0x02 TBS 索引、
    0x04 不可断行标记。实测 kindlegen 出的 AZW3 带 0x03，不剥就会解出垃圾。
    """
    end = len(record)
    remaining = flags & TRAILING_DATA_MASK
    while remaining:
        if remaining & 1:
            size = trailing_entry_size(record, end)
            if size <= 0 or size > end:
                break
            end -= size
        remaining >>= 1
    return record[:end]


__all__ = [
    "BOUNDARY_MAGIC",
    "HUFF_COMPRESSION",
    "MOBI_MAGIC",
    "PALMDOC_HEADER_SIZE",
    "MobiHeader",
    "PalmDocHeader",
    "Section",
    "decode_text",
    "looks_like_name",
    "main_section",
    "parse_exth",
    "parse_kf8_section",
    "parse_mobi_header",
    "parse_section",
    "strip_trailing_data",
    "trailing_entry_size",
]
