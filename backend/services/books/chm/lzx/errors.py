"""LZX 解码相关的异常。

单独成文件是为了避免 ``bitstream`` / ``huffman`` / ``decoder`` 互相 import
造成循环依赖。
"""

from __future__ import annotations


class LzxError(ValueError):
    """LZX 数据无法解压（位流越界、Huffman 表非法、参数不支持……）。"""


__all__ = ["LzxError"]
