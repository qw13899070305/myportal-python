"""LZX 解码子包（CHM 的 MSCompressed 内容段用）。

- :mod:`~backend.services.books.chm.lzx.bitstream` 位读取器
- :mod:`~backend.services.books.chm.lzx.huffman`   两个 Huffman 解码器
- :mod:`~backend.services.books.chm.lzx.decoder`   解码主循环（含移植出处说明）
"""

from __future__ import annotations

from .decoder import LzxDecoder
from .errors import LzxError

__all__ = ["LzxDecoder", "LzxError"]
