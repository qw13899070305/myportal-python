"""CHM 层的异常（单独成文件，避免 container / content 互相 import）。"""

from __future__ import annotations


class ChmError(ValueError):
    """CHM 结构非法 / 无法解析 / 解压失败。"""


__all__ = ["ChmError"]
