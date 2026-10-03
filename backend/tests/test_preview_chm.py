"""CHM 解析器与预览扩展测试。

分三层：

1. **LZX 解码器单元测试**：测试向量是从真实 CHM（pywin32 的 PyWin32.chm，
   2.6MB，未入库）里抽出来的压缩帧，base64 内联在本文件里，跑测试不需要样本。
2. **解析层**（``backend.services.books.chm``）：用测试里现拼的"未压缩 CHM"
   夹具（ITSF 头 + 文件长度头 + PMGL 目录块 + Uncompressed 内容段）断言
   容器解析、目录树、章节切分、图片内联、链接重写、清洗与错误兜底。
3. **展示层**（``backend.extensions.preview``）：BookPreview 渲染出来的页面，
   以及走真实 HTTP 接口的上传 + 预览。
"""

from __future__ import annotations

import base64
import struct
from pathlib import Path

import pytest

from backend.extensions.preview import find_handler
from backend.extensions.preview.chm import ChmPreview
from backend.services.books import BookError, BookParser, find_parser, parse_book
from backend.services.books.chm import ChmParser
from backend.services.books.chm.container import ChmError, ChmFile
from backend.services.books.chm.lzx import LzxDecoder, LzxError
from backend.services.books.chm.topics import parse_hhc

# ---------------------------------------------------------------------------
# 一、LZX 解码器（向量来自真实 CHM 的压缩帧）
# ---------------------------------------------------------------------------
# 样本参数（取自 PyWin32.chm 的 LZXC 控制数据与 ResetTable）：
#   window bits = 15 + log2(2) = 16（64KB 滑窗）
#   reset interval = 2 帧，block size = 32768
# 即：偶数帧是 reset 帧（可独立解码），奇数帧必须接着上一帧的滑窗解。
_WINDOW_BITS = 16
_BLOCK_SIZE = 32768

#: 第 0 帧（reset 帧，压缩后 2318 字节 -> 32768 字节，正文开头是 HTML 文档）
_FRAME0_B64 = (
    "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"
)

#: 第 1 帧（非 reset 帧，压缩后 1330 字节，开头是上一帧结尾那个标签的后半截）
_FRAME1_B64 = (
    "6B9D8wHg7ElNWsiNugvoxMjfJjs0ryTKXR6ioYOtIzRudtWGkFTLQqZHEYOeMEFV9gcJRdTjACzPvoZONfQamDGP+oEw"
    "7e2zyUqBjHkcoax0EO/2/YV2cFerFcAKaU+nYl3Y+oxEdceuh7APnuhAsDZDYOSZZiSbeYDw/0YidNjlgUHbUNYqdIuq"
    "4LR12VBa4VyOY5sJGucCr5wnxEJnDMw2GI5s34Jy9afzGvrk9npDV3ER2I9lIH/BydXPwWTDi3tHmR6hILSFVrMIosGG"
    "xaDqS8L6qKhTZ8bTetaWtBfHpd5X2nwevcutYDDjQMCJmMrm5c1VQSblUJghIVNJmS0KdDaZBxNpPsA+TKSBdD+6ilAs"
    "Z0e8KcTififQS5h10SKUHK8/Xgc6x/bMBUCHNavZ6Ym6TQltYpdGwFYZWyl0+1wLNV4m+AXaWLunSTQqewTdQO06CMZ1"
    "HohbnA+c1RVok4YoxiRHV+MLrE8vFEjsduBcG1bgSqvtpiEeTEXTA9Fm4E1egRVY4vi4pgFAKdB6WGaaXh+V3tpd1lcB"
    "lVkZQGRr7qlmxMdFzcCSigh7+jDEZLVd7HTsLKDL26ilI6D2bQ+M1JYBSNWTK5aDYcdVxRgURceZ+SmHTkJCuYKsQQeu"
    "9lUpGOn3mmom3vANsw5pphQ9Y9qmM6qxOZDNQL/s9qt92qZnXzM8Qn+5jhxm8NrRgEs5XcjRLiY4IGwbAmv7QMfAgsuJ"
    "j2PEcK1mj8NC4Q6vTqUE37QrqO5cJIiufijBZuQZnlsCMYMJ63nGclM57poapKj/xaVuiPWfy5bAcwwzOqdErDFk8/NX"
    "6mz3QF7Hgb5SmAuf4+pap7gm2dCq/m6y4Onty+2kD737T1YTwPl4UEBpP395DThDWS6AaNLdry+LtBcrjBbNhTVIHrmu"
    "nW2Mbar86LRfWNCVnbxr3d7Vsncw2CE21lxh3ppmlqemWPm7nEVfa6Ekdo8RlN5EoJwGCuT1Ufy0V+OTc6y3RLIUmkRc"
    "/SwmricToyETTpS7tVlxXctumyDGyTOxuIXh9uO4FcIjBQG8Sc0w23YNo4Qeoqx8J42oX7laAUptIfDqKeb4nBheel89"
    "u0LJ3qe4RAlWDOA6R7gKC3YsA6qTPv8nZbtVqXuLE3TrYeh0HDItW1A6aOr1zvA2SHim2d2moLYqWSxzthbX3K1Zc2pi"
    "YXaelreaTqGAxrIKpCKrLNG7LY6ilrIU14QljNWTG2atUiBXulolI7rc7W8Y769mW/rMjm2swl0U2PBUQQMFa5nASQ1l"
    "SjSCoT1yvw16LCVgzKplwErt92jVB6Jx1+3iTuIFGrAwDMKmCUz5Jz2HyJggY6xzABuHfW1EpADUe5wRzjjI+/QiPwqa"
    "S1TcA77rEdwMvjwTKnKNXcBClUHirnSVAxr2OeleL6L/W9qDcE6WhNo+EDclUfGHTu4PfIy41RWIppY2xn8A6G4qNrWd"
    "qcH3YE6UDBy4Kjnq0dW8AezykIq9Rx27lWROLNkQnL106VY69uoJADrT+sFEeiH9t3NTBBmMCyEITqzQClVUUpW0gBMg"
    "ExSS/w9lAORmlHW0ssKKZDcCk9oskmRsowqgxcUpy2tNTwnLYtZTW0dUl7iKLi6ED2GHlpUaFCDZlnCWlpNIFhaXCJYV"
    "i1ABKnoEFaqVgfR4riYuKSwpFqG8UNLJJcQapZLJl2IG+/+PsMdoWmQeg1BC2C32WTEmJvcwl0bbpY0aiVKEcXwgNosD"
    "dbmXTIOuBLwuBLEL4T9XOMsAsg=="
)

#: 第 356 帧（reset 帧，压缩后仅 92 字节 -> 32768 字节的高度重复数据）
_FRAME356_B64 = (
    "EBABAAAAAAAEAEAEDkK/Df1/75cIxAAAAAAYABgAYxB8D/s16fcABAAAAAAAAAjR3y/uDe/XdcW8a/a9AAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAACgA="
)


def test_lzx_decodes_first_frame_of_real_chm():
    """真实 CHM 的第 0 帧能解出完整 32KB，且是正常的 HTML 开头。"""
    frame = base64.b64decode(_FRAME0_B64)
    assert len(frame) == 2318

    decoder = LzxDecoder(_WINDOW_BITS)
    out = decoder.decompress(frame, _BLOCK_SIZE)

    assert len(out) == _BLOCK_SIZE
    assert out.lstrip().startswith(b"<!DOCTYPE HTML")
    assert b"<HTML>" in out[:200]
    assert out.rstrip().endswith(b"va")  # 与第 1 帧的边界（正文被 32KB 切断）


def test_lzx_chained_frame_needs_previous_frame_history():
    """第 1 帧不是 reset 帧：接着第 0 帧解才正确，丢掉滑窗直接解会失败。"""
    decoder = LzxDecoder(_WINDOW_BITS)
    first = decoder.decompress(base64.b64decode(_FRAME0_B64), _BLOCK_SIZE)
    assert len(first) == _BLOCK_SIZE

    decoder.keep_history = True
    second = decoder.decompress(base64.b64decode(_FRAME1_B64), _BLOCK_SIZE)
    assert len(second) == _BLOCK_SIZE

    # 这个字符串横跨两帧边界（前半截在第 0 帧末尾、后半截在第 1 帧开头）
    boundary = b'value="mk:@MSITStore:PyWin32.chm::/win32api__GetComputerNameEx_meth.html"'
    assert boundary in first + second
    assert boundary not in first
    assert not second.startswith(boundary)

    # 把它当成 reset 帧（强制丢弃历史）会解不出：说明帧间状态确实被用上了
    with pytest.raises(LzxError):
        LzxDecoder(_WINDOW_BITS).decompress(base64.b64decode(_FRAME1_B64), _BLOCK_SIZE)


def test_lzx_decodes_highly_repetitive_frame():
    """长匹配（重复数据）路径：92 字节压出 32KB 的周期数据。"""
    frame = base64.b64decode(_FRAME356_B64)
    assert len(frame) == 92

    decoder = LzxDecoder(_WINDOW_BITS)
    out = decoder.decompress(frame, _BLOCK_SIZE)

    assert len(out) == _BLOCK_SIZE
    pattern = out[:13]
    assert pattern == b"\x00\x00\x05\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00"
    assert out[1300:1313] == pattern
    assert out[2600:2613] == pattern
    assert out.count(b"\x00\x05\x00\x00\x00\x80") > 2000


def test_lzx_rejects_impossible_window_bits():
    with pytest.raises(LzxError):
        LzxDecoder(40)


# ---------------------------------------------------------------------------
# 二、自造夹具：一个"未压缩内容段"的最小 CHM
# ---------------------------------------------------------------------------
# 布局：ITSF 头(0x60) + 文件长度头(24) + ITSP 目录头(84) + 一个 PMGL 块 + 内容段
# 内容段里第一项是 ::DataSpace/NameList（只声明 Uncompressed），
# 后面是各个内部文件，目录项里的 offset 都相对内容段起点。

_GIF_1PX = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)

_INDEX_HTML = """<html><head><title>Index Page</title>
<style>p{color:red;behavior:url(x)} @import url(evil.css);</style>
</head><body onload="alert(1)">
<h1>Hello CHM</h1>
<script>alert('xss')</script>
<p onclick="alert(2)">Body text here</p>
<img src="pic.gif" alt="pic">
<img src="missing.png" alt="gone">
<a href="page2.htm">Next page</a>
<a href="javascript:alert(3)">bad</a>
<a href="https://example.com/">external</a>
<iframe src="https://evil.example"></iframe>
</body></html>"""

_PAGE2_HTML = (
    "<html><head><title>Second Page</title></head><body>"
    "<h1>Second body</h1><p>second paragraph</p>"
    "<a href='index.htm'>back</a></body></html>"
)

_HHC = """<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN"><HTML><BODY>
<UL>
<LI><OBJECT type="text/sitemap"><param name="Name" value="Index">
<param name="Local" value="index.htm"></OBJECT>
<UL>
<LI><OBJECT type="text/sitemap"><param name="Name" value="Second">
<param name="Local" value="mk:@MSITStore:fixture.chm::/page2.htm"></OBJECT>
</UL>
</UL>
</BODY></HTML>"""


def _enc7(value: int) -> bytes:
    """PMGL 目录项用的 7 位大端变长整数。"""
    groups = [value & 0x7F]
    value >>= 7
    while value:
        groups.append(value & 0x7F)
        value >>= 7
    groups.reverse()
    return bytes(
        (group | 0x80) if index < len(groups) - 1 else group
        for index, group in enumerate(groups)
    )


def _namelist(names: list[str]) -> bytes:
    """::DataSpace/NameList：段名列表（UTF-16LE，带长度前缀）。"""
    out = bytearray(struct.pack("<HH", 0, len(names)))
    for name in names:
        raw = name.encode("utf-16le")
        out += struct.pack("<H", len(raw) // 2) + raw + b"\x00\x00"
    struct.pack_into("<H", out, 0, len(out))
    return bytes(out)


def _system(codes: dict[int, bytes]) -> bytes:
    """/#SYSTEM：u32 版本 + 若干 (u16 code, u16 长度, 数据)。"""
    out = bytearray(struct.pack("<I", 3))
    for code, value in codes.items():
        out += struct.pack("<HH", code, len(value)) + value
    return bytes(out)


def build_chm(files: dict[str, bytes]) -> bytes:
    """把 {内部路径: 内容} 拼成一个只有 Uncompressed 内容段的 CHM。"""
    entries: dict[str, tuple[int, int, int]] = {}
    content = bytearray(_namelist(["Uncompressed"]))
    entries["::DataSpace/NameList"] = (0, 0, len(content))
    for name, payload in files.items():
        offset = len(content)
        content += payload
        entries[name] = (0, offset, len(payload))

    # PMGL 块：20 字节块头 + 目录项 + 末尾 2 字节的条目数
    chunk = bytearray(b"PMGL" + b"\x00" * 16)
    for name, (section, offset, length) in entries.items():
        raw = name.encode("utf-8")
        chunk += _enc7(len(raw)) + raw + _enc7(section) + _enc7(offset) + _enc7(length)
    while len(chunk) % 8:
        chunk += b"\x00"
    chunk += struct.pack("<H", len(entries))

    dir_offset = 0x78
    dir_header = bytearray(84)
    dir_header[0:8] = b"ITSP\x01\x00\x00\x00"
    struct.pack_into("<I", dir_header, 4, 1)  # 版本
    struct.pack_into("<I", dir_header, 8, 84)  # 目录头长度（块从这里开始）
    struct.pack_into("<I", dir_header, 16, len(chunk))  # 块大小
    struct.pack_into("<I", dir_header, 20, 2)  # density
    struct.pack_into("<I", dir_header, 24, 2)  # tree depth
    struct.pack_into("<I", dir_header, 28, 1)  # root chunk
    struct.pack_into("<I", dir_header, 32, 0)  # 第一个 PMGL 块
    struct.pack_into("<I", dir_header, 36, 0)  # 最后一个 PMGL 块
    struct.pack_into("<I", dir_header, 44, 1)  # 块总数
    struct.pack_into("<I", dir_header, 48, 0x409)  # 语言（en-US）
    dir_header[52:68] = bytes.fromhex("6a92025d2e21d0119df900a0c922e6ec")
    struct.pack_into("<I", dir_header, 68, 84)  # 目录头长度（第二处）

    content_offset = dir_offset + 84 + len(chunk)
    total_size = content_offset + len(content)

    header = bytearray(0x60)
    header[0:4] = b"ITSF"
    struct.pack_into("<I", header, 4, 3)  # 版本 3
    struct.pack_into("<I", header, 8, 0x60)  # 头长度
    struct.pack_into("<I", header, 0x14, 0x409)  # 语言（en-US）
    struct.pack_into("<QQ", header, 0x38, 0x60, 24)  # 文件长度头
    struct.pack_into("<QQ", header, 0x48, dir_offset, 84 + len(chunk))  # 目录
    struct.pack_into("<Q", header, 0x58, content_offset)  # 内容段起点

    size_header = (
        b"\xfe\x01\x00\x00" + b"\x00" * 4 + struct.pack("<Q", total_size) + b"\x00" * 8
    )
    return bytes(header) + size_header + bytes(dir_header) + bytes(chunk) + bytes(content)


def make_fixture(*, with_toc: bool = True, html: bool = True) -> bytes:
    """测试用的未压缩 CHM（默认主题 index.htm、两个页面、一张图片）。"""
    files = {
        "/#SYSTEM": _system(
            {
                0x0000: "toc.hhc".encode("utf-16le") + b"\x00\x00",
                0x0002: "index.htm".encode("utf-16le") + b"\x00\x00",
                0x0003: "Fixture CHM".encode("utf-16le") + b"\x00\x00",
            }
        ),
        "/pic.gif": _GIF_1PX,
    }
    if html:
        files["/index.htm"] = _INDEX_HTML.encode("utf-8")
        files["/page2.htm"] = _PAGE2_HTML.encode("utf-8")
    else:
        files["/readme.txt"] = b"just a text file, no html at all"
    if with_toc:
        files["/toc.hhc"] = _HHC.encode("utf-8")
    return build_chm(files)


def _write(tmp_path: Path, data: bytes, name: str = "fixture.chm") -> Path:
    target = tmp_path / name
    target.write_bytes(data)
    return target


# ---------------------------------------------------------------------------
# 三、解析层：容器
# ---------------------------------------------------------------------------


def test_container_reads_directory_and_system():
    chm = ChmFile(make_fixture())

    assert set(chm.names()) == {
        "::DataSpace/NameList",
        "/#SYSTEM",
        "/index.htm",
        "/page2.htm",
        "/pic.gif",
        "/toc.hhc",
    }
    # SYSTEM：默认主题 / 标题
    assert chm.system_string(0x0002) == "index.htm"
    assert chm.system_string(0x0003) == "Fixture CHM"
    # 内容段：Uncompressed 不压缩，直接按偏移切片
    assert chm.sections[0].name == "Uncompressed"
    assert chm.sections[0].compressed is False
    assert b"Hello CHM" in chm.read("/index.htm")
    assert chm.read("/pic.gif") == _GIF_1PX
    # 大小写不敏感 + 带不带前导斜杠都能找
    assert chm.find("PAGE2.HTM") == "/page2.htm"
    assert chm.find("/Page2.htm") == "/page2.htm"
    assert chm.read("/missing.htm") is None
    assert chm.declared_size == len(make_fixture())


def test_container_rejects_corrupt_directory():
    data = bytearray(make_fixture())
    struct.pack_into("<Q", data, 0x48, len(data) - 8)  # 目录指向文件末尾
    with pytest.raises(ChmError):
        ChmFile(bytes(data))


# ---------------------------------------------------------------------------
# 四、解析层：目录树与章节
# ---------------------------------------------------------------------------


def test_parse_hhc_tracks_nesting_and_targets():
    items = parse_hhc(_HHC, 10)
    assert [(item.level, item.title, item.target) for item in items] == [
        (0, "Index", "index.htm"),
        (1, "Second", "mk:@MSITStore:fixture.chm::/page2.htm"),
    ]


def test_parse_book_splits_chapters(tmp_path):
    path = _write(tmp_path, make_fixture())
    book = parse_book(path)

    assert book is not None
    assert book.format == "chm"
    assert book.title == "Fixture CHM"  # 来自 /#SYSTEM
    assert book.language == "en-US"  # 来自 ITSF 头的 LCID
    assert book.truncated is False
    assert book.note == ""
    assert [chapter.index for chapter in book.chapters] == [0, 1]
    # 标题：页面 <title> 优先，目录里的名字兜底
    assert [chapter.title for chapter in book.chapters] == ["Index Page", "Second Page"]
    assert [chapter.anchor for chapter in book.chapters] == ["chm-topic-0", "chm-topic-1"]

    first = book.chapters[0].html
    assert "Hello CHM" in first
    assert "data:image/gif;base64," in first  # 图片已内联
    assert 'href="#chm-topic-1"' in first  # 站内链接 -> 页内锚点
    assert "https://example.com/" in first  # 外链保留
    # text 是纯文本，标签不能再出现
    assert "Hello CHM" in book.chapters[0].text
    assert "<h1>" not in book.chapters[0].text
    assert "Body text here" in book.chapters[0].text


def test_parse_book_cleans_dangerous_markup(tmp_path):
    book = parse_book(_write(tmp_path, make_fixture()))
    html = book.chapters[0].html
    lowered = html.lower()

    assert "<script" not in lowered
    assert "alert('xss')" not in html
    assert "<iframe" not in lowered
    assert "onclick" not in lowered and "onload" not in lowered
    assert "javascript:" not in lowered
    assert 'href="#"' in html  # javascript: 链接被改写成空锚点
    # <style> 连同内容一起丢掉（共用清洗的策略），CSS 一个字都不留
    assert "<style" not in lowered
    assert "behavior" not in lowered and "@import" not in lowered
    # 内部图片内联，找不到的图片只留文档自带的 alt
    assert "data:image/gif;base64," in html
    assert "chm-image-missing" in html and "gone" in html
    assert 'src="missing.png"' not in html


def test_parse_book_falls_back_to_page_list_without_hhc(tmp_path):
    book = parse_book(_write(tmp_path, make_fixture(with_toc=False)))

    # 没有 .hhc 时目录退化成"所有 .htm 按路径排序"，章节标题取页面 <title>
    assert [chapter.title for chapter in book.chapters] == ["Index Page", "Second Page"]
    assert "back" in book.chapters[1].html


def test_parse_book_reports_truncation(tmp_path, monkeypatch):
    monkeypatch.setattr(find_parser(".chm"), "max_topics", 1)
    book = parse_book(_write(tmp_path, make_fixture()))

    assert book.truncated is True
    assert book.chapter_count == 1
    assert "只解析了前 1 个" in book.note


def test_parse_book_stops_when_html_budget_exhausted(tmp_path, monkeypatch):
    """正文体量超预算时停止续页，但第一页一定保留。"""
    monkeypatch.setattr(find_parser(".chm"), "max_html_bytes", 1)
    book = parse_book(_write(tmp_path, make_fixture()))

    assert book.truncated is True
    assert book.chapter_count == 1
    assert "Hello CHM" in book.chapters[0].html


# ---------------------------------------------------------------------------
# 五、解析层：错误兜底（一律 BookError，带中文说明）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"this is not a chm file at all", id="not-chm"),
        pytest.param(b"ITSF\x02\x00\x00\x00", id="truncated-header"),
        pytest.param(make_fixture()[:180], id="truncated-directory"),
    ],
)
def test_parse_book_raises_book_error_for_broken_files(tmp_path, payload):
    with pytest.raises(BookError) as excinfo:
        parse_book(_write(tmp_path, payload, "broken.chm"))

    assert excinfo.value.message  # 有中文说明
    assert "Preview" not in repr(excinfo.value)


def test_parse_book_rejects_unsupported_itsf_version(tmp_path):
    data = bytearray(make_fixture())
    struct.pack_into("<I", data, 4, 1)  # ITSF 版本 1
    with pytest.raises(BookError) as excinfo:
        parse_book(_write(tmp_path, bytes(data)))
    assert "版本" in excinfo.value.message


def test_parse_book_without_html_topics(tmp_path):
    with pytest.raises(BookError) as excinfo:
        parse_book(_write(tmp_path, make_fixture(html=False)))
    assert "没有网页正文" in excinfo.value.message


def test_parse_book_returns_none_for_unknown_extension(tmp_path):
    target = tmp_path / "notes.txt"
    target.write_text("hello", encoding="utf-8")
    assert parse_book(target) is None


def test_container_is_tolerant_to_tail_truncation():
    """尾部被截断（最后一个文件缺字节）时仍应尽量解析，而不是整本放弃。"""
    chm = ChmFile(make_fixture()[:-32])
    assert chm.system_string(0x0002) == "index.htm"
    assert b"Hello CHM" in chm.read("/index.htm")


def test_parse_book_missing_file(tmp_path):
    with pytest.raises(BookError) as excinfo:
        parse_book(tmp_path / "nope.chm")
    assert "无法读取" in excinfo.value.message


# ---------------------------------------------------------------------------
# 六、展示层：预览扩展与接口
# ---------------------------------------------------------------------------


def test_chm_parser_and_preview_are_registered():
    parser = find_parser(".chm")
    assert isinstance(parser, ChmParser)
    assert isinstance(parser, BookParser)
    assert parser.priority == 20

    handler = find_handler(".chm")
    assert isinstance(handler, ChmPreview)
    assert handler.priority == 20
    assert handler.extensions == frozenset({".chm"})
    # 其它格式不受影响
    assert type(find_handler(".txt")).__name__ == "TextPreview"
    assert type(find_handler(".exe")).__name__ == "FallbackPreview"


def test_chm_preview_renders_book_page(tmp_path):
    preview = ChmPreview().render(_write(tmp_path, make_fixture()))

    assert preview.kind == "html"
    html = preview.html or ""
    assert "Hello CHM" in html and "Second body" in html
    # 展示层自己的外壳：标题、目录、章节锚点
    assert "Fixture CHM" in html
    assert "book-toc" in html
    assert "id='chm-topic-0'" in html and "id='chm-topic-1'" in html
    assert "data:image/gif;base64," in html
    assert "内容过大" not in html


def test_chm_preview_message_page_for_broken_file(tmp_path):
    preview = ChmPreview().render(_write(tmp_path, b"not a chm at all", "broken.chm"))

    assert preview.kind == "html"
    assert "打不开这本书" in (preview.html or "")


def test_chm_preview_endpoint(client, user_headers):
    """走一遍真实接口：上传 .chm -> GET /preview。"""
    upload = client.post(
        "/api/v1/files/upload",
        files={"file": ("manual.chm", make_fixture(), "application/octet-stream")},
        headers=user_headers,
    )
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["id"]

    response = client.get(f"/api/v1/files/{file_id}/preview", headers=user_headers)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/html")
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "Hello CHM" in response.text
    assert "<script" not in response.text.lower()
    assert "data:image/gif;base64," in response.text


def test_book_json_endpoint_shares_the_same_parse(client, user_headers):
    """同一份解析结果也能以纯数据 JSON 给客户端（手机 APP 那条线）。"""
    upload = client.post(
        "/api/v1/files/upload",
        files={"file": ("data.chm", make_fixture(), "application/octet-stream")},
        headers=user_headers,
    )
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["id"]

    response = client.get(f"/api/v1/files/{file_id}/book", headers=user_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["format"] == "chm"
    assert body["title"] == "Fixture CHM"
    assert body["chapter_count"] == 2
    assert [chapter["title"] for chapter in body["chapters"]] == ["Index Page", "Second Page"]
    assert [chapter["anchor"] for chapter in body["chapters"]] == ["chm-topic-0", "chm-topic-1"]
    assert "Hello CHM" in body["chapters"][0]["html"]
    assert "Hello CHM" in body["chapters"][0]["text"]
    assert "<script" not in response.text.lower()
