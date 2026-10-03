"""HUFF/CDIC 解压（MOBI 的 compression=17480）。

表结构（MobileRead 的 MOBI 格式页；字段含义与 calibre / kindleunpack 的实现一致）：

HUFF 记录
    ``HUFF`` + u32 头长(24) + u32 dict1 偏移 + u32 dict2 偏移
    - dict1：256 个 u32，每个 8 位前缀一项。低 5 位是码长、0x80 是终结标志、
      高 24 位是最大码；非终结项要先按 dict2 把码长逐位加长。
    - dict2：32 组 (mincode, maxcode)，对应码长 1..32。
CDIC 记录
    ``CDIC`` + u32 头长(16) + u32 词条数 + u32 每记录索引位数。
    头 16 字节之后是 u16 偏移表（偏移相对第 16 字节），每个条目前 2 字节是
    ``长度 | 0x8000``：带 0x8000 是叶子，否则是要递归解包的子串。

表里只要有一处不对就抛 :class:`MobiFormatError`，由解析器决定降级行为。
"""

from __future__ import annotations

from backend.services.books.mobi.errors import MobiFormatError
from backend.services.books.mobi.pdb import Reader

#: HUFF 记录固定的前 8 字节（魔数 + 头长 24）
_HUFF_MAGIC = b"HUFF\x00\x00\x00\x18"
#: CDIC 记录固定的前 8 字节（魔数 + 头长 16）
_CDIC_MAGIC = b"CDIC\x00\x00\x00\x10"
#: 码长的最大值（dict2 覆盖 1..32）
_MAX_CODE_LEN = 32


class HuffCdicReader:
    """HUFF/CDIC 解码器：先读表，再逐记录解压。"""

    #: 词条递归解包的深度上限（防构造出来的超深词条）
    _MAX_DEPTH = 8
    #: 单个词条解包后的字节上限
    _MAX_PHRASE = 1 << 20

    def __init__(self, huff_records: list[bytes], cdic_records: list[bytes]) -> None:
        if not huff_records or not cdic_records:
            raise MobiFormatError("HUFF/CDIC 记录缺失")
        self._dict1: list[tuple[int, bool, int]] = []
        self._mincode = [0] * (_MAX_CODE_LEN + 1)
        self._maxcode = [0xFFFFFFFF] * (_MAX_CODE_LEN + 1)
        self._dictionary: list[tuple[bool, bytes]] = []
        self._cache: dict[int, bytes] = {}
        self._load_huff(huff_records[0])
        for record in cdic_records:
            self._load_cdic(record)
        if not self._dictionary:
            raise MobiFormatError("HUFF/CDIC 词条为空")

    # ---------------- 建表 ----------------

    def _load_huff(self, huff: bytes) -> None:
        reader = Reader(huff)
        if reader.slice(0, 8) != _HUFF_MAGIC:
            raise MobiFormatError("HUFF 记录头不合法")
        dict1_offset = reader.u32(8)
        dict2_offset = reader.u32(12)
        for index in range(256):
            value = reader.u32(dict1_offset + index * 4)
            codelen = value & 0x1F
            if codelen == 0:
                # 码长为 0 的解码循环会原地打转，直接判废
                raise MobiFormatError("HUFF 表里出现 0 码长")
            maxcode = ((((value >> 8) + 1) << (32 - codelen)) - 1) & 0xFFFFFFFF
            self._dict1.append((codelen, bool(value & 0x80), maxcode))
        for length in range(1, _MAX_CODE_LEN + 1):
            low = reader.u32(dict2_offset + (length - 1) * 8)
            high = reader.u32(dict2_offset + (length - 1) * 8 + 4)
            self._mincode[length] = (low << (32 - length)) & 0xFFFFFFFF
            self._maxcode[length] = (((high + 1) << (32 - length)) - 1) & 0xFFFFFFFF

    def _load_cdic(self, cdic: bytes) -> None:
        reader = Reader(cdic)
        if reader.slice(0, 8) != _CDIC_MAGIC:
            raise MobiFormatError("CDIC 记录头不合法")
        phrases = reader.u32(8)
        bits = reader.u32(12)
        if bits > 16:
            raise MobiFormatError(f"CDIC 每记录索引位数异常：{bits}")
        room = min(1 << bits, max(0, phrases - len(self._dictionary)))
        for index in range(room):
            start = 16 + reader.u16(16 + index * 2)
            length_flags = reader.u16(start)
            end = min(start + 2 + (length_flags & 0x7FFF), len(cdic))
            self._dictionary.append((bool(length_flags & 0x8000), cdic[start + 2 : end]))

    # ---------------- 解码 ----------------

    def unpack(self, data: bytes, limit: int) -> bytes:
        """解压一条正文记录，最多输出 ``limit`` 字节。"""
        output = bytearray()
        self._unpack_into(data, output, limit, 0)
        return bytes(output)

    def _unpack_into(self, data: bytes, output: bytearray, limit: int, depth: int) -> None:
        if depth > self._MAX_DEPTH:
            raise MobiFormatError("HUFF/CDIC 词条嵌套过深")
        if not data or len(output) >= limit:
            return
        padded = data + b"\x00" * 8
        bits_left = len(data) * 8
        position = 0
        window = int.from_bytes(padded[0:8], "big")
        available = 32
        while bits_left > 0 and len(output) < limit:
            if available <= 0:
                position += 4
                if position + 8 > len(padded):
                    break
                window = int.from_bytes(padded[position : position + 8], "big")
                available += 32
            code = (window >> available) & 0xFFFFFFFF
            codelen, terminator, maxcode = self._dict1[code >> 24]
            if not terminator:
                # 码长超过 8 位：先按 dict1 的提示加长，再取 dict2 给的区间
                while codelen < _MAX_CODE_LEN and code < self._mincode[codelen]:
                    codelen += 1
                maxcode = self._maxcode[codelen]
            available -= codelen
            bits_left -= codelen
            if bits_left < 0:
                break
            index = (maxcode - code) >> (32 - codelen)
            if index < 0 or index >= len(self._dictionary):
                raise MobiFormatError(f"HUFF/CDIC 词条索引越界：{index}")
            leaf, payload = self._dictionary[index]
            if not leaf:
                if index not in self._cache:
                    expanded = bytearray()
                    self._unpack_into(payload, expanded, self._MAX_PHRASE, depth + 1)
                    self._cache[index] = bytes(expanded)
                payload = self._cache[index]
            output += payload[: limit - len(output)]


def looks_like_text(data: bytes) -> bool:
    """判断解出来的字节流像不像正文。

    HUFF/CDIC 表要是解错了，产物基本是高熵乱码；用它当最后一道闸门，
    宁可退回"暂不支持"，也不要把乱码塞给用户。
    """
    if not data:
        return False
    sample = data[:65536]
    control = sum(1 for byte in sample if byte < 0x20 and byte not in (0x09, 0x0A, 0x0D))
    return control * 20 < len(sample)  # 控制字符占比 < 5%


__all__ = ["HuffCdicReader", "looks_like_text"]
