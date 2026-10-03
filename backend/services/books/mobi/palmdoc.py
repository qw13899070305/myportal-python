"""PalmDOC LZ77 解压（MOBI 的 compression=2）。

规则（MobileRead 的 PalmDOC 页）——逐字节读 ``c``：

- ``0x00``            原样输出一个 0x00
- ``0x01``-``0x08``   后面 ``c`` 个字节原样输出
- ``0x09``-``0x7F``   原样输出 ``c``
- ``0x80``-``0xBF``   再读一字节组成 16 位 ``v``：距离 ``(v>>3)&0x7FF``、
                      长度 ``(v&7)+3``，从已输出内容里往回复制（允许重叠）
- ``0xC0``-``0xFF``   输出空格 + ``(c ^ 0x80)``

Mobipocket 的正文按 4096 字节一块独立压缩，所以本函数是**逐记录**调用的。
"""

from __future__ import annotations

#: 距离/长度对的分支边界
_LENGTH_PAIR_MIN = 0x80
_LENGTH_PAIR_MAX = 0xBF
_BYTE_PAIR_MIN = 0xC0


def decompress(data: bytes, limit: int) -> bytes:
    """解压一段 PalmDOC 数据，最多输出 ``limit`` 字节。

    数据损坏（距离越界）时停止解压并返回已有内容——宁可少显示一段，
    也不要吐出一堆乱码。
    """
    output = bytearray()
    position = 0
    size = len(data)
    while position < size and len(output) < limit:
        value = data[position]
        position += 1
        if value == 0:
            output.append(0)
        elif value <= 8:
            output += data[position : position + value]
            position += value
        elif value <= _LENGTH_PAIR_MIN - 1:
            output.append(value)
        elif value <= _LENGTH_PAIR_MAX:
            if position >= size:
                break
            pair = (value << 8) | data[position]
            position += 1
            distance = (pair >> 3) & 0x7FF
            length = (pair & 7) + 3
            if distance <= 0 or distance > len(output):
                break
            for _ in range(length):
                if len(output) >= limit:
                    break
                output.append(output[-distance])
        else:
            output.append(0x20)
            if len(output) < limit:
                output.append(value ^ _LENGTH_PAIR_MIN)
    return bytes(output)


__all__ = ["decompress"]
