"""CHM 容器结构：ITSF 头 / 文件长度头 / ITSP 目录（PMGL 块）。

只负责"文件里有什么、某个内部文件在哪"，内容段的解压与取字节在
:mod:`~backend.services.books.chm.content`。这一层不认识 HTML，也不产任何
面向用户的文案（那是 :mod:`backend.services.books.chm` 的事）。

布局回顾（真实文件里的样子）::

    ITSF 头（0x60 字节）
      +0x38 文件长度段(offset,length)  +0x48 目录段(offset,length)
      +0x58 内容段起点（v3 才有）
    文件长度头（24 字节，魔数 FE 01 00 00）
    目录段：ITSP 头（84 字节）+ 若干 PMGL/PMGI 块（每块 chunk_size 字节）
    内容段：第一个内部文件固定是 ::DataSpace/NameList（声明内容段名字）
"""

from __future__ import annotations

import struct

from backend.core.logger import logger

from .content import ContentReader, Entry, Section
from .errors import ChmError
from .lzx import LzxError
from .textutil import decode_system_string

_ITSF_MAGIC = b"ITSF"
_ITSP_MAGIC = b"ITSP\x01\x00\x00\x00"
_PMGL_MAGIC = b"PMGL"
_PMGI_MAGIC = b"PMGI"
_FILE_SIZE_MAGIC = b"\xfe\x01\x00\x00"


def _read_7bit(data: bytes, pos: int) -> tuple[int, int]:
    """PMGL 目录项里的 7 位大端变长整数。"""
    value = 0
    while True:
        if pos >= len(data):
            raise ChmError("目录项被截断")
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos


def _u16(data: bytes, pos: int) -> int:
    return struct.unpack_from("<H", data, pos)[0]


def _u32(data: bytes, pos: int) -> int:
    return struct.unpack_from("<I", data, pos)[0]


def _u64(data: bytes, pos: int) -> int:
    return struct.unpack_from("<Q", data, pos)[0]


class ChmFile:
    """只读的 CHM 容器。

    目录项统一按 **CHM 内部路径**（``/`` 分隔，形如 ``/html/index.htm``）索引，
    查找大小写不敏感（Windows 帮助文件里大小写经常对不上），并且带不带前导
    ``/`` 都能找到。
    """

    def __init__(self, data: bytes) -> None:
        self._data = data
        if len(data) < 0x60 or not data.startswith(_ITSF_MAGIC):
            raise ChmError("不是 CHM 文件（缺少 ITSF 头）")
        self.version = _u32(data, 4)
        if self.version < 2:
            raise ChmError(f"不支持 ITSF 版本 {self.version}（仅支持 2 / 3）")
        self.language = _u32(data, 0x14)

        # 文件长度头只是自校验用，坏了也不影响读取
        file_size_offset = _u64(data, 0x38)
        if file_size_offset and data.startswith(_FILE_SIZE_MAGIC, file_size_offset):
            self.declared_size = _u64(data, file_size_offset + 8)
        else:
            self.declared_size = 0

        self.directory_offset = _u64(data, 0x48)
        self._listing: dict[str, Entry] = {}
        self._listing_lower: dict[str, str] = {}
        self._read_directory(self.directory_offset)
        self._read_listing_chunks(self.directory_offset)
        if not self._listing:
            raise ChmError("CHM 目录为空或已损坏")

        content_offset = _u64(data, 0x58) if self.version >= 3 else 0
        if not content_offset:
            # 版本 2 没有内容段起点字段：目录段之后就是内容段
            content_offset = (
                self.directory_offset
                + self.directory_header_length
                + self.chunk_size * self.total_chunks
            )
        self.content_offset = content_offset
        self._content = ContentReader(data, content_offset, self._entry)
        self.sections: list[Section] = self._content.sections

    # ---------------- 目录 ----------------

    def _read_directory(self, directory_offset: int) -> None:
        data = self._data
        if directory_offset + 84 > len(data):
            raise ChmError("目录头越界")
        if not data.startswith(_ITSP_MAGIC, directory_offset):
            raise ChmError("目录头（ITSP）签名不匹配")
        version = _u32(data, directory_offset + 4)
        if version != 1:
            raise ChmError(f"不支持 ITSP 版本 {version}")
        self.directory_header_length = _u32(data, directory_offset + 8)
        self.chunk_size = _u32(data, directory_offset + 16)
        self.density = _u32(data, directory_offset + 20)
        self.total_chunks = _u32(data, directory_offset + 44)
        if self.chunk_size <= 24 or self.chunk_size > (1 << 22):
            raise ChmError("目录块尺寸异常")
        if self.total_chunks > 1_000_000:
            raise ChmError("目录块数量异常")

    def _read_listing_chunks(self, directory_offset: int) -> None:
        data = self._data
        pos = directory_offset + self.directory_header_length
        for _ in range(self.total_chunks):
            body = data[pos : pos + self.chunk_size]
            pos += self.chunk_size
            if len(body) < 24:
                break
            magic = body[:4]
            if magic == _PMGI_MAGIC:
                continue  # 索引块，文件清单在 PMGL 里
            if magic != _PMGL_MAGIC:
                continue
            num_entries = _u16(body, len(body) - 2)
            cursor = 20
            for _ in range(num_entries):
                try:
                    name_len, cursor = _read_7bit(body, cursor)
                    if name_len <= 0 or cursor + name_len > len(body):
                        raise ChmError("目录项名称越界")
                    raw_name = body[cursor : cursor + name_len]
                    cursor += name_len
                    section_index, cursor = _read_7bit(body, cursor)
                    offset, cursor = _read_7bit(body, cursor)
                    length, cursor = _read_7bit(body, cursor)
                except (ChmError, IndexError, struct.error):
                    break
                name = self._decode_name(raw_name)
                if not name:
                    continue
                self._listing[name] = (section_index, offset, length)
                self._listing_lower.setdefault(name.lower(), name)

    @staticmethod
    def _decode_name(raw: bytes) -> str:
        for encoding in ("utf-8", "cp1252"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("latin-1")

    # ---------------- 查找 / 读取 ----------------

    def _entry(self, name: str) -> Entry | None:
        real = self.find(name)
        return self._listing.get(real) if real else None

    def find(self, name: str) -> str | None:
        """按 CHM 内部路径查找真实存在的文件名（大小写不敏感）。

        CHM 目录里的名字总带前导 ``/``，而 SYSTEM / .hhc 里引用的路径通常不带，
        所以两种写法都试一遍。
        """
        name = (name or "").replace("\\", "/").strip()
        if not name:
            return None
        for candidate in (name, "/" + name.lstrip("/")):
            if candidate in self._listing:
                return candidate
            real = self._listing_lower.get(candidate.lower())
            if real is not None:
                return real
        return None

    def exists(self, name: str) -> bool:
        return self.find(name) is not None

    def size(self, name: str) -> int:
        entry = self._entry(name or "")
        return entry[2] if entry else 0

    def names(self) -> list[str]:
        """全部内部文件路径（含 ``::DataSpace/...`` 这类系统项）。"""
        return list(self._listing)

    def read(self, name: str) -> bytes | None:
        """读出内部文件内容；解压失败返回 ``None``（调用方决定怎么降级）。"""
        real = self.find(name)
        if real is None:
            return None
        try:
            return self._content.read_entry(self._listing[real])
        except (ChmError, LzxError, IndexError, struct.error) as exc:
            logger.warning(f"[chm] 读取内部文件 {real} 失败: {exc}")
            return None

    def read_entry(self, entry: Entry) -> bytes:
        return self._content.read_entry(entry)

    @property
    def decoded_bytes(self) -> int:
        """已解压字节数（调用方拿它做预算控制）。"""
        return self._content.decoded_bytes

    # ---------------- SYSTEM ----------------

    def system_entries(self) -> dict[int, bytes]:
        """解析 ``/#SYSTEM``：返回 ``{code: 原始字节}``。"""
        raw = self.read("/#SYSTEM")
        if not raw or len(raw) < 4:
            return {}
        entries: dict[int, bytes] = {}
        cursor = 4
        while cursor + 4 <= len(raw):
            code = _u16(raw, cursor)
            length = _u16(raw, cursor + 2)
            cursor += 4
            if length <= 0 or cursor + length > len(raw):
                break
            entries.setdefault(code, raw[cursor : cursor + length])
            cursor += length
        return entries

    def system_string(self, code: int) -> str:
        """取 ``/#SYSTEM`` 里的某个字符串（默认主题、标题……）。"""
        return decode_system_string(self.system_entries().get(code, b""))


__all__ = ["ChmError", "ChmFile", "Section"]
