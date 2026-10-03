"""LZX 解码器主循环（CHM 的 MSCompressed 内容段用它解压）。

# CHM 容器与 LZX 解码算法移植改写自 binary-refinery（BSD-3-Clause, © Jesko Hüttenhain）
# 的 refinery/lib/chm.py 与 refinery/lib/seven/lzx.py（含 seven/huffman.py），
# 已去掉对 refinery 框架的依赖：StructReader / uint32array / INF 等换成自包含实现
# （BitReader 见 bitstream.py，Huffman 表见 huffman.py），并按预览/解析场景改成
# 逐帧惰性解码 + 预算控制。

调用方式与 CHM 的 reset table 对应：第 ``i`` 帧若落在 reset 点上，先置
``keep_history = False``，解完再置回 ``True``，后续帧即可引用滑窗历史。
"""

from __future__ import annotations

from .bitstream import BitReader
from .errors import LzxError
from .huffman import HuffmanDecoder, HuffmanDecoder7b

_BLOCK_TYPE_NUM_BITS = 3
_BLOCK_TYPE_VERBATIM = 1
_BLOCK_TYPE_ALIGNED = 2
_BLOCK_TYPE_UNCOMPRESSED = 3
_NUM_HUFFMAN_BITS = 16
_NUM_REPS = 3
_NUM_LEN_SLOTS = 8
_MATCH_MIN_LEN = 2
_NUM_LEN_SYMBOLS = 249
_NUM_ALIGN_LEVEL_BITS = 3
_NUM_ALIGN_BITS = 3
_ALIGN_TABLE_SIZE = 1 << _NUM_ALIGN_BITS
_NUM_POS_SLOTS = 50
_NUM_POS_LEN_SLOTS = _NUM_POS_SLOTS * _NUM_LEN_SLOTS
_LZX_TABLE_SIZE = 256 + _NUM_POS_LEN_SLOTS
_LVL_TABLE_SIZE = 20
_NUM_LEVEL_BITS = 4
_LEVEL_SYM_ZERO = 17
_LEVEL_SYM_SAME = 19
_LEVEL_SYM_ZERO_START = 4
_LEVEL_SYM_ZERO_NUM_BITS = 4
_LEVEL_SYM_SAME_NUM_BITS = 1
_LEVEL_SYM_SAME_START = 4
_NUM_DICT_BITS_MIN = 15
_NUM_DICT_BITS_MAX = 21
_NUM_LINEAR_POS_SLOT_BITS = 17
_NUM_POWER_POS_SLOTS = 38
_INF = float("inf")


def _memzap(data) -> None:
    n = len(data)
    if n:
        data[:] = bytes(n)


def _x86_filter(
    win: bytearray, start: int, end: int, processed_size: int, translate_size: int
) -> None:
    """LZX 的 E8 调用地址变换（CHM 基本用不到，保留以保持算法完整）。"""
    size = (end - start) - 10
    if size <= 0:
        return
    save = win[start + size + 4]
    win[start + size + 4] = 0xE8
    i = 0
    while True:
        while win[start + i] != 0xE8:
            i += 1
        if i >= size:
            break
        i += 1
        v = int.from_bytes(win[start + i : start + i + 4], "little", signed=True)
        pos = 1 - (processed_size + i)
        if v >= pos and v < translate_size:
            v += pos if v >= 0 else translate_size
            v &= 0xFFFFFFFF
            win[start + i : start + i + 4] = v.to_bytes(4, "little")
        i += 4
    win[start + size + 4] = save


class LzxDecoder:
    """LZX 解压器：每次 :meth:`decompress` 处理 CHM 的一帧。"""

    def __init__(self, num_dict_bits: int = _NUM_DICT_BITS_MIN) -> None:
        self.set_params(num_dict_bits)  # 先校验窗口位数，避免按非法值分配内存
        self.keep_history = False
        self._win = bytearray(1 << num_dict_bits)
        self._win_size = 1 << num_dict_bits
        self._pos = 0
        self._write_pos = 0
        self._over_dict = False
        self._skip_byte = False
        self._is_uncompressed_block = False
        self._num_align_bits = 0
        self._unpack_block_size = 0
        self._x86_translate_size = 0
        self._x86_processed_size = 0
        self._reps = [1, 1, 1]
        self._bits = BitReader()
        self._lzx_decoder = HuffmanDecoder(_NUM_HUFFMAN_BITS, _LZX_TABLE_SIZE)
        self._len_decoder = HuffmanDecoder(_NUM_HUFFMAN_BITS, _NUM_LEN_SYMBOLS)
        self._align_decoder = HuffmanDecoder7b(_ALIGN_TABLE_SIZE)
        self._level_decoder = HuffmanDecoder(_NUM_HUFFMAN_BITS, _LVL_TABLE_SIZE, 7)
        self._lzx_levels = bytearray(_LZX_TABLE_SIZE)
        self._len_levels = bytearray(_NUM_LEN_SYMBOLS)
        self.set_params(num_dict_bits)

    # ---------------- 位流与表 ----------------

    def _read_table(self, levels, num_symbols: int) -> None:
        lvls = bytearray(_LVL_TABLE_SIZE)
        bits = self._bits
        for i in range(_LVL_TABLE_SIZE):
            lvls[i] = bits.read_bits_small(_NUM_LEVEL_BITS)
        self._level_decoder.build(lvls)
        i = 0
        while i < num_symbols:
            sym = self._level_decoder.decode(bits)
            num = 0
            if sym <= _NUM_HUFFMAN_BITS:
                delta = levels[i] - sym
                if delta < 0:
                    delta += _NUM_HUFFMAN_BITS + 1
                levels[i] = delta
                i += 1
                continue
            if sym < _LEVEL_SYM_SAME:
                sym -= _LEVEL_SYM_ZERO
                num += bits.read_bits_small(_LEVEL_SYM_ZERO_NUM_BITS + sym)
                num += _LEVEL_SYM_ZERO_START
                num += sym << _LEVEL_SYM_ZERO_NUM_BITS
                symbol = 0
            elif sym == _LEVEL_SYM_SAME:
                num += _LEVEL_SYM_SAME_START
                num += bits.read_bits_small(_LEVEL_SYM_SAME_NUM_BITS)
                sym = self._level_decoder.decode(bits)
                if sym > _NUM_HUFFMAN_BITS:
                    raise LzxError("Huffman 表：位长越界")
                delta = levels[i] - sym
                if delta < 0:
                    delta += _NUM_HUFFMAN_BITS + 1
                symbol = delta
            else:
                raise LzxError("Huffman 表：符号越界")
            idx = i + num
            if idx > num_symbols:
                raise LzxError("Huffman 表：下标越界")
            while True:
                levels[i] = symbol
                i += 1
                if i >= idx:
                    break

    def _read_tables(self) -> bool:
        bits = self._bits
        if self._skip_byte and bits.direct_read_byte() != 0:
            raise LzxError("未压缩块的对齐字节非 0")
        bits.normalize_big()
        block_type = bits.read_bits_small(_BLOCK_TYPE_NUM_BITS)
        if block_type > _BLOCK_TYPE_UNCOMPRESSED:
            raise LzxError(f"未知的 LZX 块类型 {block_type}")
        self._unpack_block_size = bits.read_bits_small(16)
        self._unpack_block_size <<= 8
        self._unpack_block_size |= bits.read_bits_small(8)
        self._unpack_block_size &= 0xFFFFFFFF
        self._is_uncompressed_block = block_type == _BLOCK_TYPE_UNCOMPRESSED
        self._skip_byte = False
        if self._is_uncompressed_block:
            self._skip_byte = bool(self._unpack_block_size & 1)
            if not bits.prepare_uncompressed():
                raise LzxError("未压缩块前的填充位非 0")
            if bits.get_remaining_bytes() < _NUM_REPS * 4:
                raise LzxError("未压缩块缺少 reps 表")
            for i in range(_NUM_REPS):
                rep = bits.read_int32()
                if rep > self._win_size:
                    raise LzxError("reps 表数值超出窗口")
                self._reps[i] = rep
            return True
        if block_type == _BLOCK_TYPE_ALIGNED:
            levels = bytearray(_ALIGN_TABLE_SIZE)
            self._num_align_bits = _NUM_ALIGN_BITS
            for i in range(_ALIGN_TABLE_SIZE):
                levels[i] = bits.read_bits_small(_NUM_ALIGN_LEVEL_BITS)
            self._align_decoder.build(levels)
        else:
            self._num_align_bits = 64

        lvl = memoryview(self._lzx_levels)
        end = 0
        for count in (256, self._num_pos_len_slots):
            self._read_table(lvl[end:], count)
            end += count
        _memzap(lvl[end:_LZX_TABLE_SIZE])
        self._lzx_decoder.build(self._lzx_levels)
        self._read_table(self._len_levels, _NUM_LEN_SYMBOLS)
        self._len_decoder.build(self._len_levels)
        return False

    # ---------------- 主循环 ----------------

    def _flush(self) -> None:
        if not self._x86_translate_size or self._pos <= self._write_pos:
            return
        _x86_filter(
            self._win,
            self._write_pos,
            self._pos,
            self._x86_processed_size,
            self._x86_translate_size,
        )
        self._x86_processed_size += self._pos - self._write_pos
        if self._x86_processed_size >= (1 << 30):
            self._x86_translate_size = 0

    def _decompress(self, cur_size) -> bool:
        win = self._win
        win_size = self._win_size
        bits = self._bits
        eof_halt = False
        if not self.keep_history or not self._is_uncompressed_block:
            bits.normalize_big()
        if not self.keep_history:
            self._skip_byte = False
            self._unpack_block_size = 0
            _memzap(self._lzx_levels)
            _memzap(self._len_levels)
            self._x86_translate_size = 0
            if bits.read_bits_small(1):
                v = bits.read_bits_small(16) << 16
                v |= bits.read_bits_small(16)
                self._x86_translate_size = v
            self._x86_processed_size = 0
            self._reps[0] = 1
            self._reps[1] = 1
            self._reps[2] = 1

        if not cur_size:
            cur_size = _INF
            eof_halt = True

        lzx_decode = self._lzx_decoder.decode
        len_decode = self._len_decoder.decode
        align_decode = self._align_decoder.decode
        reps = self._reps

        while cur_size > 0:
            if bits.overflow > 4:
                raise LzxError("LZX 位流越界")
            if self._unpack_block_size == 0:
                self._read_tables()
                continue
            next_size = min(self._unpack_block_size, cur_size)
            if self._is_uncompressed_block:
                rem = bits.get_remaining_bytes()
                if rem == 0:
                    if eof_halt:
                        return False
                    raise LzxError("未压缩块数据不足")
                if next_size > rem:
                    next_size = rem
                if self._pos + next_size > win_size:
                    raise LzxError("未压缩块输出超出窗口")
                bits.copy_to(win[self._pos :], next_size)
                self._pos += next_size
                cur_size -= next_size
                self._unpack_block_size -= next_size
                if (
                    self._skip_byte
                    and self._unpack_block_size == 0
                    and cur_size == 0
                    and bits.is_one_direct_byte_left()
                ):
                    self._skip_byte = False
                    if bits.direct_read_byte() != 0:
                        raise LzxError("未压缩块的对齐字节非 0")
                continue
            if self._pos + next_size > win_size:
                raise LzxError("LZX 输出超出窗口")
            cur_size -= next_size
            self._unpack_block_size -= next_size
            while next_size > 0:
                if bits.overflow > 4:
                    raise LzxError("LZX 位流越界")
                sym = lzx_decode(bits)
                if eof_halt and bits.overflow > 2:
                    return False
                if sym < 256:
                    win[self._pos] = sym
                    next_size -= 1
                    self._pos += 1
                    continue
                sym -= 256
                if sym >= self._num_pos_len_slots:
                    raise LzxError("LZX 长度槽越界")
                pos_slot, len_slot = divmod(sym, _NUM_LEN_SLOTS)
                length = _MATCH_MIN_LEN + len_slot
                if len_slot == _NUM_LEN_SLOTS - 1:
                    len_temp = len_decode(bits)
                    if len_temp >= _NUM_LEN_SYMBOLS:
                        raise LzxError("LZX 长度符号越界")
                    length = _MATCH_MIN_LEN + _NUM_LEN_SLOTS - 1 + len_temp
                if pos_slot < _NUM_REPS:
                    dist = reps[pos_slot]
                    reps[pos_slot] = reps[0]
                    reps[0] = dist
                else:
                    if pos_slot < _NUM_POWER_POS_SLOTS:
                        num_direct_bits = (pos_slot >> 1) - 1
                        dist = (2 | (pos_slot & 1)) << num_direct_bits
                    else:
                        num_direct_bits = _NUM_LINEAR_POS_SLOT_BITS
                        dist = (pos_slot - 0x22) << _NUM_LINEAR_POS_SLOT_BITS
                    dist &= 0xFFFFFFFF
                    if num_direct_bits >= self._num_align_bits:
                        dist += (
                            bits.read_bits_small(num_direct_bits - _NUM_ALIGN_BITS)
                            << _NUM_ALIGN_BITS
                        )
                        align_temp = align_decode(bits)
                        if align_temp >= _ALIGN_TABLE_SIZE:
                            raise LzxError("LZX 对齐符号越界")
                        dist += align_temp
                    else:
                        dist += bits.read_bits_big(num_direct_bits)
                    dist -= _NUM_REPS - 1
                    reps[2] = reps[1]
                    reps[1] = reps[0]
                    reps[0] = dist
                if length > next_size:
                    raise LzxError("LZX 匹配长度越界")
                pos = self._pos
                if dist > pos and not self._over_dict:
                    raise LzxError("LZX 匹配距离越界")
                next_size -= length
                src_pos = pos - dist
                if src_pos < 0:
                    src_pos %= win_size
                if dist >= length and src_pos + length <= win_size and pos + length <= win_size:
                    # 前后不重叠时用切片拷贝，比逐字节快很多
                    win[pos : pos + length] = win[src_pos : src_pos + length]
                    self._pos = pos + length
                else:
                    dst_pos = pos
                    for _ in range(length):
                        win[dst_pos] = win[src_pos]
                        dst_pos += 1
                        src_pos += 1
                        if src_pos >= win_size:
                            src_pos = 0
                    self._pos = dst_pos
        return bits.was_finished_ok()

    # ---------------- 对外接口 ----------------

    def set_params(self, num_dict_bits: int) -> None:
        if num_dict_bits < _NUM_DICT_BITS_MIN or num_dict_bits > _NUM_DICT_BITS_MAX:
            raise LzxError(f"LZX 窗口位数 {num_dict_bits} 非法")
        self._num_dict_bits = num_dict_bits
        num_pos_slots = num_dict_bits * 2 if num_dict_bits < 20 else 34 + (1 << (num_dict_bits - 17))
        self._num_pos_len_slots = num_pos_slots * _NUM_LEN_SLOTS

    def decompress(self, data: bytes, expected_output_size: int = 0) -> bytes:
        """解一帧，返回这一帧新产出的字节（``expected_output_size=0`` 表示解到数据尽头）。"""
        if not self.keep_history:
            self._pos = 0
            self._over_dict = False
        elif self._pos == self._win_size:
            self._pos = 0
            self._over_dict = True
        if expected_output_size > self._win_size - self._pos:
            raise LzxError("期望输出长度超过窗口剩余空间")
        self._write_pos = self._pos
        self._bits.initialize(data)
        self._decompress(expected_output_size)
        self._flush()
        return bytes(self._win[self._write_pos : self._pos])


__all__ = ["LzxDecoder"]
