"""LZX 用的两个规范 Huffman 解码器。

移植改写自 binary-refinery（BSD-3-Clause, © Jesko Hüttenhain）的
``refinery/lib/seven/huffman.py``（其本身是 7-Zip 的转写）；出处详见
:mod:`backend.services.books.chm.lzx.decoder` 的文件头说明。

与上游的差别只有一处：上游用 ``refinery.lib.array.uint32array``，
这里换成普通 list（省掉一个依赖，索引还更快）。
"""

from __future__ import annotations

from .bitstream import BitReader
from .errors import LzxError


class HuffmanDecoder:
    """主 Huffman 解码器：9 位查表 + 逐位回退。"""

    _NUM_PAIR_LEN_BITS = 4
    _PAIR_LEN_MASK = (1 << _NUM_PAIR_LEN_BITS) - 1

    def __init__(self, num_bits_max: int, num_symbols: int, num_table_bits: int = 9) -> None:
        self.num_bits_max = num_bits_max
        self.num_symbols = num_symbols
        self.num_table_bits = num_table_bits
        self._limits = [0] * (num_bits_max + 2)
        self._poses = [0] * (num_bits_max + 1)
        self._lens = [0] * (1 << num_table_bits)
        self._symbols = [0] * num_symbols

    def build(self, lens) -> bool:
        """按码长表建表（``lens`` 里第 i 项是符号 i 的码长，0 表示不出现）。"""
        num_bits_max = self.num_bits_max
        num_symbols = self.num_symbols
        num_table_bits = self.num_table_bits
        max_value = 1 << num_bits_max

        counts = [0] * (num_bits_max + 1)
        for sym in range(num_symbols):
            counts[lens[sym]] += 1

        limits = self._limits
        poses = self._poses
        limits[0] = 0
        start_pos = 0
        count_sum = 0

        for i in range(1, num_bits_max + 1):
            count = counts[i]
            start_pos += count << (num_bits_max - i)
            if start_pos > max_value:
                raise LzxError("Huffman 表非法：起始位置越界")
            limits[i] = start_pos
            counts[i] = count_sum
            poses[i] = count_sum
            count_sum += count
            count_sum &= 0xFFFFFFFF

        counts[0] = count_sum
        poses[0] = count_sum
        limits[num_bits_max + 1] = max_value

        table = self._lens
        symbols = self._symbols
        for sym in range(num_symbols):
            length = lens[sym]
            if not length:
                continue
            offset = counts[length]
            counts[length] += 1
            symbols[offset] = sym
            if length <= num_table_bits:
                offset -= poses[length]
                num = 1 << (num_table_bits - length)
                val = length | (sym << self._NUM_PAIR_LEN_BITS)
                pos = (limits[length - 1] >> (num_bits_max - num_table_bits)) + (
                    offset << (num_table_bits - length)
                )
                for k in range(num):
                    table[pos + k] = val
        return True

    def decode(self, bits: BitReader) -> int:
        limits = self._limits
        num_bits_max = self.num_bits_max
        num_table_bits = self.num_table_bits
        val = bits.get_value(num_bits_max)
        if val < limits[num_table_bits]:
            pair = self._lens[val >> (num_bits_max - num_table_bits)]
            bits.move_position(pair & self._PAIR_LEN_MASK)
            return pair >> self._NUM_PAIR_LEN_BITS
        num_bits = num_table_bits + 1
        while val >= limits[num_bits]:
            num_bits += 1
        if num_bits > num_bits_max:
            return 0xFFFFFFFF
        bits.move_position(num_bits)
        index = self._poses[num_bits] + ((val - limits[num_bits - 1]) >> (num_bits_max - num_bits))
        return self._symbols[index]


class HuffmanDecoder7b:
    """对齐块用的 7 位查表 Huffman 解码器。"""

    _NUM_PAIR_LEN_BITS = 3

    def __init__(self, num_symbols: int) -> None:
        self.num_symbols = num_symbols
        self._lens = bytearray(1 << 7)

    def build(self, lens) -> bool:
        num_symbols = self.num_symbols
        num_bits_max = 7
        num_pair_len_bits = self._NUM_PAIR_LEN_BITS
        counts = [0] * (num_bits_max + 1)
        poses = [0] * (num_bits_max + 1)
        limits = [0] * (num_bits_max + 1)

        for sym in range(num_symbols):
            counts[lens[sym]] += 1

        max_value = 1 << num_bits_max
        start_pos = 0
        count_sum = 0
        for i in range(1, num_bits_max + 1):
            count = counts[i]
            start_pos += count << (num_bits_max - i)
            if start_pos > max_value:
                raise LzxError("对齐 Huffman 表非法：起始位置越界")
            limits[i] = start_pos
            counts[i] = count_sum
            poses[i] = count_sum
            count_sum += count
            count_sum &= 0xFFFFFFFF
        counts[0] = count_sum
        poses[0] = count_sum

        table = self._lens
        for sym in range(num_symbols):
            length = lens[sym]
            if not length:
                continue
            offset = counts[length]
            counts[length] += 1
            offset -= poses[length]
            num = 1 << (num_bits_max - length)
            val = length | (sym << num_pair_len_bits)
            pos = limits[length - 1] + (offset << (num_bits_max - length))
            for k in range(num):
                table[pos + k] = val

        limit = limits[num_bits_max]
        for k in range((1 << num_bits_max) - limit):
            table[limit + k] = 0xF8
        return True

    def decode(self, bits: BitReader) -> int:
        val = bits.get_value(7)
        pair = self._lens[val]
        bits.move_position(pair & 0x7)
        return pair >> 3


__all__ = ["HuffmanDecoder", "HuffmanDecoder7b"]
