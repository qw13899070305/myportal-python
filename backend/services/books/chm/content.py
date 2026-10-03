"""CHM 内容段：::DataSpace/NameList、未压缩段、LZX 压缩段与逐帧读取。

未压缩段（段名 ``Uncompressed``）直接按偏移切片；压缩段用 ResetTable 把
解压流切成若干帧，帧按 reset interval 分组——组内第一帧重置滑窗、后续帧
沿用历史，因此同一组里可以从组起点直接开解，不必从头解整个文件。
"""

from __future__ import annotations

import math
import struct
from collections.abc import Callable
from dataclasses import dataclass, field

from backend.core.logger import logger

from .errors import ChmError
from .lzx import LzxDecoder, LzxError

_LZXC_MAGIC = b"LZXC"

#: LZX 变换（reset table）GUID：CHM 与 HLP 各一种，目录里出现的是大写形式
LZX_TRANSFORM_GUIDS = (
    "7FC28940-9D31-11D0-9B27-00A0C91E9C7C",
    "0A9007C6-4076-11D3-8789-0000F8105754",
)

#: LZX 滑窗位数允许范围（对应 32KB ~ 2MB 窗口）
MIN_DICT_BITS = 15
MAX_DICT_BITS = 21

#: ::DataSpace/NameList 里表示"这一段没压缩"的段名
UNCOMPRESSED_SECTION = "uncompressed"

#: 帧缓存上限（超过就整体清空，避免大文件把内存吃满）
MAX_CACHED_FRAMES = 512

#: 目录项 = (内容段序号, 段内偏移, 长度)
Entry = tuple[int, int, int]
#: 按内部路径查目录项（大小写不敏感）
Lookup = Callable[[str], "Entry | None"]


def _u16(data: bytes, pos: int) -> int:
    return struct.unpack_from("<H", data, pos)[0]


def _u32(data: bytes, pos: int) -> int:
    return struct.unpack_from("<I", data, pos)[0]


def _u64(data: bytes, pos: int) -> int:
    return struct.unpack_from("<Q", data, pos)[0]


@dataclass
class Section:
    """一个内容段在**文件中的绝对位置**（偏移已折算过基准段）。"""

    index: int
    name: str
    offset: int
    length: int
    compressed: bool = False
    window_bits: int = MIN_DICT_BITS
    reset_interval: int = 0
    block_size: int = 32768
    frame_offsets: list[int] = field(default_factory=list)
    uncompressed_size: int = 0

    @property
    def frame_count(self) -> int:
        return len(self.frame_offsets)

    def frame_length(self, index: int) -> int:
        """第 ``index`` 帧解压后应有多少字节（0 = 让解码器解到数据尽头）。"""
        block = self.block_size or 32768
        total = self.uncompressed_size
        if total:
            remaining = total - index * block
            if remaining <= 0:
                return block
            return block if remaining > block else remaining
        if index >= self.frame_count - 1:
            return 0
        return block


class ContentReader:
    """内容段解析 + 按目录项取字节（含 LZX 逐帧惰性解码）。

    ``lookup`` 由 :class:`~backend.services.books.chm.container.ChmFile` 提供
    （按路径找目录项），这样本模块不必认识目录结构。
    """

    def __init__(self, data: bytes, content_offset: int, lookup: Lookup) -> None:
        self._data = data
        self._lookup = lookup
        self.sections: list[Section] = []
        #: 已解压字节数（调用方拿它做预算控制）
        self.decoded_bytes = 0
        self._frames: dict[tuple[int, int], bytes] = {}
        self._lzx_state: dict[int, tuple[LzxDecoder, int, int]] = {}
        self._read_sections(content_offset)

    # ---------------- 段表 ----------------

    def _read_sections(self, content_offset: int) -> None:
        blob = self._aux_blob("::DataSpace/NameList", content_offset)
        if blob is None or len(blob) < 4:
            raise ChmError("找不到 ::DataSpace/NameList，无法确定内容段")
        names = self._parse_namelist(blob)
        if not names:
            raise ChmError("CHM 未声明任何内容段")

        raw_region_length = len(self._data) - content_offset
        for index, name in enumerate(names):
            if name.strip().lower() == UNCOMPRESSED_SECTION:
                self.sections.append(
                    Section(index=index, name=name, offset=content_offset, length=raw_region_length)
                )
                continue
            if not self.sections:
                raise ChmError("压缩内容段缺少基准段（Uncompressed）")
            self.sections.append(self._read_compressed_section(index, name, self.sections[0]))

    @staticmethod
    def _parse_namelist(blob: bytes) -> list[str]:
        count = _u16(blob, 2)
        names: list[str] = []
        cursor = 4
        for _ in range(count):
            if cursor + 2 > len(blob):
                break
            chars = _u16(blob, cursor)
            cursor += 2
            names.append(blob[cursor : cursor + chars * 2].decode("utf-16le", "replace"))
            cursor += chars * 2 + 2  # 末尾还有一个 WORD 的 0
        return names

    def _read_compressed_section(self, index: int, name: str, base: Section) -> Section:
        prefix = f"::DataSpace/Storage/{name}/"
        content = self._lookup(prefix + "Content")
        if content is None:
            raise ChmError(f"内容段 {name} 缺少 Content 文件")
        content_section, offset, length = content
        if content_section != base.index:
            raise ChmError(f"内容段 {name} 的基准段异常（{content_section}）")
        section = Section(
            index=index,
            name=name,
            offset=base.offset + offset,
            length=length,
            compressed=True,
        )

        control = self._aux_blob(prefix + "ControlData", base.offset)
        if control is None or not control.startswith(_LZXC_MAGIC, 4):
            raise ChmError(f"内容段 {name} 缺少 LZXC 控制数据（可能不是 LZX 压缩）")
        section.reset_interval = _u32(control, 12)
        window_field = _u32(control, 16)
        if window_field > 0:
            section.window_bits = 15 + int(round(math.log2(window_field)))
        if not MIN_DICT_BITS <= section.window_bits <= MAX_DICT_BITS:
            logger.warning(
                f"[chm] 内容段 {name} 窗口位数 {section.window_bits} 超出范围，按 16 处理"
            )
            section.window_bits = 16
        if section.reset_interval <= 0:
            section.reset_interval = 1

        span = self._aux_blob(prefix + "SpanInfo", base.offset)
        if span is not None and len(span) >= 8:
            section.uncompressed_size = _u64(span, 0)

        for guid in LZX_TRANSFORM_GUIDS:
            reset = self._aux_blob(
                f"{prefix}Transform/{{{guid}}}/InstanceData/ResetTable", base.offset
            )
            if reset is None:
                continue
            self._read_reset_table(section, reset)
            break
        if not section.frame_offsets:
            raise ChmError(f"内容段 {name} 缺少 ResetTable，无法定位压缩帧")
        return section

    @staticmethod
    def _read_reset_table(section: Section, blob: bytes) -> None:
        if len(blob) < 40:
            raise ChmError("ResetTable 内容不完整")
        version = _u32(blob, 0)
        if version not in (2, 3):
            raise ChmError(f"不支持 ResetTable 版本 {version}")
        count = _u32(blob, 4)
        entry_size = _u32(blob, 8)
        header_size = _u32(blob, 12)
        section.uncompressed_size = section.uncompressed_size or _u64(blob, 16)
        block_size = _u64(blob, 32)
        if entry_size != 8 or not block_size:
            raise ChmError("ResetTable 描述异常")
        if header_size + count * 8 > len(blob):
            raise ChmError("ResetTable 偏移表越界")
        section.block_size = block_size
        section.frame_offsets = [_u64(blob, header_size + 8 * i) for i in range(count)]

    def _aux_blob(self, name: str, base_offset: int) -> bytes | None:
        """读取辅助文件（NameList / ControlData / SpanInfo / ResetTable）。

        它们通常放在未压缩的基准段里（偏移相对该段），万一落在已解析的内容段
        里也按段偏移折算。
        """
        entry = self._lookup(name)
        if entry is None:
            return None
        section_index, offset, length = entry
        if section_index < len(self.sections):
            start = self.sections[section_index].offset + offset
        else:
            start = base_offset + offset
        return self._data[start : start + length]

    # ---------------- 取字节 ----------------

    def read_entry(self, entry: Entry) -> bytes:
        section_index, offset, length = entry
        if length <= 0 or offset < 0:
            return b""
        if section_index >= len(self.sections):
            raise ChmError(f"目录项指向不存在的内容段 {section_index}")
        section = self.sections[section_index]
        if not section.compressed:
            start = section.offset + offset
            return self._data[start : start + length]
        block = section.block_size or 32768
        first = offset // block
        last = (offset + length - 1) // block
        if last >= section.frame_count:
            raise ChmError("目录项超出内容段范围")
        chunks = [self._frame(section, i) for i in range(first, last + 1)]
        blob = b"".join(chunks)
        start = offset - first * block
        return blob[start : start + length]

    def _frame_bytes(self, section: Section, index: int) -> bytes:
        start = section.offset + section.frame_offsets[index]
        if index + 1 < section.frame_count:
            end = section.offset + section.frame_offsets[index + 1]
        else:
            end = section.offset + section.length
        return self._data[start:end]

    def _frame(self, section: Section, index: int) -> bytes:
        """解出第 ``index`` 帧（惰性、带缓存；必要时从本组 reset 点重放）。"""
        key = (section.index, index)
        cached = self._frames.get(key)
        if cached is not None:
            return cached

        interval = max(1, section.reset_interval)
        group = (index // interval) * interval
        decoder, next_frame, cur_group = self._lzx_state.get(section.index, (None, -1, -1))
        if decoder is None or cur_group != group or next_frame > index:
            decoder = LzxDecoder(section.window_bits)
            next_frame = group
            cur_group = group

        error: Exception | None = None
        for frame_index in range(next_frame, index + 1):
            raw = self._frame_bytes(section, frame_index)
            if frame_index % interval == 0:
                decoder.keep_history = False
            try:
                out = decoder.decompress(raw, section.frame_length(frame_index))
            except (LzxError, IndexError, struct.error) as exc:
                error = exc
                break
            finally:
                decoder.keep_history = True
            self._frames[(section.index, frame_index)] = out
            self.decoded_bytes += len(out)
            next_frame = frame_index + 1

        self._lzx_state[section.index] = (decoder, next_frame, cur_group)
        if len(self._frames) > MAX_CACHED_FRAMES:
            self._frames.clear()
        if key not in self._frames:
            raise ChmError(f"LZX 帧 {index} 解压失败: {error}")
        return self._frames[key]


__all__ = ["ContentReader", "Section"]
