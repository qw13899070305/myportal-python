"""LZX 位读取器。

移植改写自 binary-refinery（BSD-3-Clause, © Jesko Hüttenhain）的
``refinery/lib/seven/lzx.py`` 里 7-Zip BitDecoder 的转写版；出处详见
:mod:`backend.services.books.chm.lzx.decoder` 的文件头说明。
"""

from __future__ import annotations

from .errors import LzxError


class BitReader:
    """按 LZX 的方式取位：先填满 16/32 位，再从中截取。"""

    __slots__ = ("_buf", "_pos", "_bitpos", "_value", "overflow")

    def __init__(self, data: bytes = b"") -> None:
        self.initialize(data)

    def initialize(self, data: bytes) -> None:
        self._buf = data
        self._pos = 0
        self._bitpos = 0
        self._value = 0
        #: 越过缓冲区末尾的次数（每次补 0xFFFF 记 2）
        self.overflow = 0

    def get_remaining_bytes(self) -> int:
        return len(self._buf) - self._pos

    def was_finished_ok(self) -> bool:
        if self._pos != len(self._buf):
            return False
        if (self._bitpos >> 4) * 2 != self.overflow:
            return False
        num_bits = self._bitpos & 15
        return not ((self._value >> (self._bitpos - num_bits)) & ((1 << num_bits) - 1))

    def normalize_small(self) -> None:
        if self._bitpos > 16:
            return
        pos = self._pos
        buf = self._buf
        if pos >= len(buf) - 1:
            val = 0xFFFF
            self.overflow += 2
        else:
            val = int.from_bytes(buf[pos : pos + 2], "little")
            self._pos += 2
        self._value = ((self._value & 0xFFFF) << 16) | val
        self._bitpos += 16

    def normalize_big(self) -> None:
        self.normalize_small()
        self.normalize_small()

    def get_value(self, num_bits: int) -> int:
        return (self._value >> (self._bitpos - num_bits)) & ((1 << num_bits) - 1)

    def move_position(self, num_bits: int) -> None:
        self._bitpos -= num_bits
        self.normalize_small()

    def read_bits_small(self, num_bits: int) -> int:
        self._bitpos -= num_bits
        val = (self._value >> self._bitpos) & ((1 << num_bits) - 1)
        self.normalize_small()
        return val

    def read_bits_big(self, num_bits: int) -> int:
        self._bitpos -= num_bits
        val = (self._value >> self._bitpos) & ((1 << num_bits) - 1)
        self.normalize_big()
        return val

    def prepare_uncompressed(self) -> bool:
        """未压缩块要求把剩余位补齐到字节边界（且必须全为 0）。"""
        if self.overflow > 0:
            raise LzxError("位流已越界，无法切换到未压缩块")
        num_bits = self._bitpos - 16
        if num_bits > 0 and ((self._value >> 16) & ((1 << num_bits) - 1)):
            return False
        self._pos -= 2
        self._bitpos = 0
        return True

    def read_int32(self) -> int:
        pos = self._pos
        end = pos + 4
        self._pos = end
        return int.from_bytes(self._buf[pos:end], "little")

    def copy_to(self, dest: bytearray, size: int) -> None:
        pos = self._pos
        end = pos + size
        self._pos = end
        dest[:size] = self._buf[pos:end]

    def is_one_direct_byte_left(self) -> bool:
        return self._pos == len(self._buf) - 1 and self.overflow == 0

    def direct_read_byte(self) -> int:
        pos = self._pos
        buf = self._buf
        if pos >= len(buf):
            self.overflow += 1
            return 0xFF
        value = buf[pos]
        self._pos += 1
        return value


__all__ = ["BitReader"]
