"""PalmDB 容器：78 字节文件头 + 记录表。

记录表紧跟在文件头之后，每项 8 字节——**先 4 字节偏移（只有低 24 位有效），
再 4 字节属性 + UID**（这一点容易记反）。本模块只认容器，不碰 MOBI 语义。
"""

from __future__ import annotations

from backend.services.books.mobi.errors import MobiFormatError

#: PDB 文件头长度
HEADER_SIZE = 78
#: 认得的 PalmDB 类型：MOBI/AZW（BOOKMOBI）与老式纯 PalmDOC（TEXtREAd）
KNOWN_TYPES = (b"BOOKMOBI", b"TEXtREAd")
#: 偏移字段只有低 24 位有效，高 8 位是标志
OFFSET_MASK = 0xFFFFFF
#: 找特殊记录时最多扫多少条（正常电子书远小于它）
SCAN_LIMIT = 4096


class Reader:
    """大端读取器：越界一律抛 :class:`MobiFormatError`，调用方不用自己算长度。"""

    __slots__ = ("data",)

    def __init__(self, data: bytes) -> None:
        self.data = data

    def slice(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise MobiFormatError(f"读取越界 offset={offset} size={size} len={len(self.data)}")
        return self.data[offset : offset + size]

    def has(self, offset: int, size: int = 1) -> bool:
        return offset >= 0 and size >= 0 and offset + size <= len(self.data)

    def u16(self, offset: int) -> int:
        return int.from_bytes(self.slice(offset, 2), "big")

    def u32(self, offset: int) -> int:
        return int.from_bytes(self.slice(offset, 4), "big")


class PalmDatabase:
    """PalmDB 文件：记录表切片 + 按序号取记录。"""

    def __init__(self, raw: bytes) -> None:
        if len(raw) < HEADER_SIZE:
            raise MobiFormatError("文件太小，不够一个 PalmDB 头")
        reader = Reader(raw)
        kind = reader.slice(60, 8)
        if kind not in KNOWN_TYPES:
            raise MobiFormatError(f"PalmDB 类型不是 BOOKMOBI/TEXtREAd：{kind!r}")
        count = reader.u16(76)
        if count <= 0 or HEADER_SIZE + count * 8 > len(raw):
            raise MobiFormatError("记录表为空或越界")

        size = len(raw)
        starts = [reader.u32(HEADER_SIZE + index * 8) & OFFSET_MASK for index in range(count)]
        self._records: list[tuple[int, int]] = []
        for index, start in enumerate(starts):
            # 偏移一律夹到文件长度内：被截断的文件只会得到空记录，不会越界
            start = min(start, size)
            following = starts[index + 1] if index + 1 < count else size
            self._records.append((start, min(max(following, start), size)))

        self.data = raw
        self.kind = kind
        self.database_name = (
            reader.slice(0, 32).split(b"\x00", 1)[0].decode("cp1252", errors="replace").strip()
        )

    def __len__(self) -> int:
        return len(self._records)

    def record(self, index: int) -> bytes:
        """取一条记录；越界或落在文件外的（截断文件）返回空串。"""
        if index < 0 or index >= len(self._records):
            return b""
        start, end = self._records[index]
        return self.data[start:end]

    def record_slice(self, start: int, count: int) -> list[bytes]:
        """取连续若干条记录，空记录（越界/被截断）直接丢掉。"""
        begin = max(0, start)
        indices = range(begin, begin + max(0, count))
        return [record for record in (self.record(index) for index in indices) if record]

    def find_record(self, prefix: bytes) -> int | None:
        """找第一条以 ``prefix`` 开头的记录（用于定位 KF8 的 BOUNDARY）。"""
        for index in range(1, min(len(self._records), SCAN_LIMIT)):
            if self.data.startswith(prefix, self._records[index][0]):
                return index
        return None


__all__ = ["HEADER_SIZE", "KNOWN_TYPES", "PalmDatabase", "Reader"]
