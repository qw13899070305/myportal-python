"""AZW3 / MOBI 预览与解析测试。

样本全部在测试里现场合成（PalmDB 头 + 记录表 + PalmDOC/MOBI 头 + EXTH + 正文），
不往仓库里提交任何二进制；/tmp/books 下有真实样本时再做一次端到端核对。

覆盖两条线：
- 解析层 ``backend/services/books/mobi``：Book 元数据、分章、清洗、DRM、HUFF/CDIC、
  截断、额外数据、损坏文件
- 展示层 ``backend/extensions/preview/mobi.py``：BookPreview 薄壳渲染出的页面
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from backend.extensions.preview import find_handler
from backend.extensions.preview import supported_extensions as preview_extensions
from backend.extensions.preview.mobi import MobiPreview
from backend.services.books import BookParser, clear_cache, parse_book
from backend.services.books import registry as book_registry
from backend.services.books import supported_extensions as book_extensions
from backend.services.books.model import Book, BookError
from backend.services.books.mobi.huffcdic import HuffCdicReader
from backend.services.books.mobi.palmdoc import decompress as palmdoc_decompress

#: 真实样本（不提交进仓库，别人环境里自动跳过）
REAL_AZW3 = Path("/tmp/books/alice.azw3")
REAL_MOBI = Path("/tmp/books/alice.mobi")

#: compression = 17480 表示 HUFF/CDIC
_HUFF = 17480

#: 1×1 的透明 PNG，用来验证 <img recindex> 内联
TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c63000100000500010d0a2db40000"
    "000049454e44ae426082"
)


# ---------------- 合成样本的积木 ----------------


def _palmdoc_literals(data: bytes) -> bytes:
    """全字面量 PalmDOC 流：每 ≤8 字节前面加一个长度字节（1..8）。"""
    out = bytearray()
    for start in range(0, len(data), 8):
        chunk = data[start : start + 8]
        out.append(len(chunk))
        out += chunk
    return bytes(out)


def _palmdoc_copy(distance: int, length: int) -> bytes:
    """构造距离/长度复制对（0x80-0xBF 开头的两字节）。"""
    assert 1 <= distance <= 0x7FF and 3 <= length <= 10
    value = (distance << 3) | (length - 3)
    return bytes([0x80 | (value >> 8), value & 0xFF])


def _pdb(records: list[bytes], *, kind: bytes = b"BOOKMOBI", name: str = "Synthetic") -> bytes:
    """打包成 PalmDB（记录表每项：先 4 字节偏移（低 24 位），再 4 字节属性）。"""
    table = bytearray()
    position = 78 + len(records) * 8 + 2  # 真实文件的记录表后还有 2 字节空隙
    for record in records:
        table += (position & 0xFFFFFF).to_bytes(4, "big")
        table += (0).to_bytes(4, "big")  # 属性 + UID
        position += len(record)

    header = bytearray(78)
    header[0:32] = name.encode("cp1252")[:31].ljust(32, b"\x00")
    header[60:68] = kind
    header[68:72] = (0x12345678).to_bytes(4, "big")  # unique id seed
    header[72:76] = (0).to_bytes(4, "big")  # next record list
    header[76:78] = len(records).to_bytes(2, "big")
    return bytes(header) + bytes(table) + b"\x00\x00" + b"".join(records)


def _exth(entries: list[tuple[int, bytes]]) -> bytes:
    """EXTH 头：identifier + length + count + 若干 (type, length, data)。"""
    body = b"".join(struct.pack(">II", kind, len(value) + 8) + value for kind, value in entries)
    payload = b"EXTH" + struct.pack(">II", len(body) + 12, len(entries)) + body
    return payload + b"\x00" * ((-len(payload)) % 4)  # 补齐到 4 字节（不计入 length）


def _encode(value: str, encoding: int) -> bytes:
    """按样本声明的 text_encoding 编码字符串（1252 -> cp1252，否则 UTF-8）。"""
    return value.encode("cp1252" if encoding == 1252 else "utf-8", errors="replace")


def _record0(
    text_records: int,
    *,
    compression: int = 2,
    text_length: int = 0,
    encoding: int = 65001,
    file_version: int = 6,
    mobi_type: int = 2,
    title: str = "合成样本",
    author: str = "合成作者",
    language: str = "",
    encryption: int = 0,
    drm_count: int = 0,
    first_image_index: int = 0,
    extra_data_flags: int = 0,
    huff: tuple[int, int, int, int] | None = None,
) -> bytes:
    """构造记录 0：PalmDOC 头 + MOBI 头（232 字节）+ EXTH + 全名。"""
    header_length = 232
    mobi = bytearray(header_length)
    mobi[0:4] = b"MOBI"
    struct.pack_into(">I", mobi, 0x04, header_length)
    struct.pack_into(">I", mobi, 0x08, mobi_type)
    struct.pack_into(">I", mobi, 0x0C, encoding)
    struct.pack_into(">I", mobi, 0x10, 0x5A5A5A5A)  # unique id
    struct.pack_into(">I", mobi, 0x14, file_version)
    struct.pack_into(">I", mobi, 0x40, 1 + text_records)  # first non-book index
    struct.pack_into(">I", mobi, 0x5C, first_image_index)
    if huff is not None:
        struct.pack_into(">II", mobi, 0x60, huff[0], huff[1])
        struct.pack_into(">II", mobi, 0x68, huff[2], huff[3])
    struct.pack_into(">I", mobi, 0x70, 0x40)  # EXTH flags
    struct.pack_into(">I", mobi, 0x98, 0xFFFFFFFF)  # DRM offset
    struct.pack_into(">I", mobi, 0x9C, drm_count)
    struct.pack_into(">H", mobi, 0xB0, 1)  # first content record
    struct.pack_into(">H", mobi, 0xB2, 1 + text_records)
    struct.pack_into(">I", mobi, 0xE0, extra_data_flags)

    extra = [(524, _encode(language, encoding))] if language else []
    exth = _exth([(503, _encode(title, encoding)), (100, _encode(author, encoding)), *extra])
    head = bytearray()
    head += struct.pack(">HHIHHHH", compression, 0, text_length, text_records, 4096, encryption, 0)
    head += mobi
    head += exth
    head += b"\x00" * ((-len(head)) % 4)
    full_name = _encode(title, encoding)
    struct.pack_into(">II", head, 16 + 0x44, len(head), len(full_name))
    head += full_name
    return bytes(head)


def _book(
    payload: bytes,
    *,
    compression: int = 2,
    text_records: list[bytes] | None = None,
    text_length: int | None = None,
    images: list[bytes] | None = None,
    extra_records: list[bytes] = (),
    extra_data_flags: int = 0,
    extra_suffix: bytes = b"",
    kind: bytes = b"BOOKMOBI",
    **record0_kwargs,
) -> bytes:
    """把一段正文（默认 PalmDOC 全字面量）打包成完整的电子书字节流。"""
    if text_records is None:
        stream = _palmdoc_literals(payload) if compression == 2 else payload
        text_records = [stream]
    text_records = [record + extra_suffix for record in text_records]
    images = images or []
    first_image_index = 1 + len(text_records) + len(extra_records) if images else 0
    record0 = _record0(
        len(text_records),
        compression=compression,
        text_length=len(payload) if text_length is None else text_length,
        first_image_index=first_image_index,
        extra_data_flags=extra_data_flags,
        **record0_kwargs,
    )
    return _pdb([record0, *text_records, *extra_records, *images], kind=kind, name="Synthetic")


def _write(tmp_path: Path, name: str, data: bytes) -> Path:
    target = tmp_path / name
    target.write_bytes(data)
    return target


def _parse(path: Path, ext: str | None = None) -> Book:
    clear_cache()
    book = parse_book(path, ext)
    assert book is not None
    return book


def _html_of(path: Path) -> str:
    preview = MobiPreview().render(path)
    assert preview.kind == "html", preview
    assert preview.html
    return preview.html


def _all_html(book: Book) -> str:
    return "".join(chapter.html for chapter in book.chapters)


# ---------------- 两层都要注册上 ----------------


def test_preview_extension_is_registered():
    for ext in (".azw3", ".mobi"):
        handler = find_handler(ext)
        assert type(handler).__name__ == "MobiPreview", f"{ext} 匹配到了 {handler!r}"
    handler = find_handler(".azw3")
    assert handler.name == "mobi"
    assert handler.priority == 20
    assert handler.extensions == frozenset({".azw3", ".mobi"})
    assert {".azw3", ".mobi"} <= preview_extensions()
    assert type(find_handler(".txt")).__name__ == "TextPreview"  # 兜底不能抢


def test_book_parser_is_registered():
    assert "mobi" in book_registry.names
    parser = book_registry.get("mobi")
    assert isinstance(parser, BookParser)
    assert parser.extensions == frozenset({".azw3", ".mobi"})
    assert {".azw3", ".mobi"} <= book_extensions()


# ---------------- PalmDOC LZ77 ----------------


def test_palmdoc_decompress_handles_all_byte_kinds():
    stream = bytearray()
    stream += _palmdoc_literals(b"hello")
    stream.append(0x00)  # 0x00 -> 原样一个 0x00
    stream.append(0x41)  # 0x09-0x7F -> 原样
    stream += b"\xc1\xc2"  # 0xC0-0xFF -> 每字节展开成「空格 + (c ^ 0x80)」
    assert palmdoc_decompress(bytes(stream), 1 << 20) == b"hello\x00A A B"


def test_palmdoc_decompress_copies_repeats_and_overlaps():
    # 距离 8、长度 8：把刚输出的 8 字节再复制一遍
    stream = bytearray(_palmdoc_literals(b"abcdefgh"))
    stream += _palmdoc_copy(8, 8)
    assert palmdoc_decompress(bytes(stream), 1 << 20) == b"abcdefghabcdefgh"

    # 距离 2、长度 6（重叠复制）：ab + ababab = abababab
    stream = bytearray(_palmdoc_literals(b"ab"))
    stream += _palmdoc_copy(2, 6)
    assert palmdoc_decompress(bytes(stream), 1 << 20) == b"abababab"
    assert len(palmdoc_decompress(bytes(stream), 3)) == 3  # 长度上限


def test_palmdoc_decompress_stops_on_broken_distance():
    stream = _palmdoc_literals(b"abc") + _palmdoc_copy(50, 5)
    assert palmdoc_decompress(stream, 1 << 20) == b"abc"


# ---------------- 解析层：KF8 / AZW3 ----------------


KF8_TEXT = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<html xmlns="http://www.w3.org/1999/xhtml"><head>'
    "<title>不该出现的内部标题</title><style>p{color:red}</style></head><body>"
    '<h1 id="kf8">KF8-BODY-MARKER</h1>'
    '<p onclick="alert(1)">正文第一段 &amp; 更多</p>'
    '<script>alert("xss")</script>'
    "<mbp:pagebreak/>"
    "<h2>第二章</h2><p>中文正文</p></body></html>"
).encode("utf-8")


def test_parse_kf8_builds_clean_book(tmp_path):
    path = _write(
        tmp_path,
        "kf8.azw3",
        _book(KF8_TEXT, file_version=8, title="合成书名", author="合成作者", language="zh"),
    )
    book = _parse(path)
    html = _all_html(book)

    # 元数据（纯数据，与页面无关）
    assert book.format == "mobi"
    assert book.title == "合成书名"
    assert book.author == "合成作者"
    assert book.language == "zh"
    assert book.truncated is False
    assert book.note == ""

    # 按 <mbp:pagebreak/> 分成两章，text 与 html 都有内容
    assert book.chapter_count == 2
    assert [chapter.anchor for chapter in book.chapters] == ["mobi-0", "mobi-1"]
    assert book.chapters[0].title == "KF8-BODY-MARKER"
    assert book.chapters[1].title == "第二章"
    assert all(chapter.text.strip() for chapter in book.chapters)
    assert book.char_count > 0

    # 正文与清洗
    assert "KF8-BODY-MARKER" in html
    assert "正文第一段" in html and "更多" in html and "中文正文" in html
    assert "<script" not in html.lower()
    assert "xss" not in html
    assert "onclick" not in html
    assert "p{color:red}" not in html  # <style> 连内容一起丢
    assert "mbp:" not in html
    assert "不该出现的内部标题" not in html  # <head> 整段去掉
    assert "http://www.w3.org/1999/xhtml" not in html


def test_parse_splits_on_chapter_class(tmp_path):
    """KF8 常见的 <div class="chapter"> 也要能分章（真实 azw3 就靠它）。"""
    text = (
        '<html><body><div class="chapter"><h2>第一章 起点</h2><p>AAA</p></div>'
        '<div class="chapter"><h2>第二章 终点</h2><p>BBB</p></div></body></html>'
    ).encode("utf-8")
    book = _parse(_write(tmp_path, "chapters.azw3", _book(text, file_version=8)))

    assert book.chapter_count == 2
    assert book.chapters[0].title == "第一章 起点"
    assert book.chapters[1].title == "第二章 终点"
    assert "AAA" in book.chapters[0].text and "BBB" not in book.chapters[0].text
    assert "BBB" in book.chapters[1].text


def test_parse_mobi6_inlines_recindex_image(tmp_path):
    text = (
        "<html><head><guide><reference type='toc' filepos=0000001 /></guide></head><body>"
        "<p>MOBI6-BODY-MARKER</p><mbp:pagebreak/>"
        '<p><img recindex="00001" align="baseline" alt="cover" /></p>'
        '<p><img recindex="00009" alt="missing" /></p>'
        "</body></html>"
    ).encode("utf-8")
    book = _parse(_write(tmp_path, "legacy.mobi", _book(text, images=[TINY_PNG])))
    html = _all_html(book)

    assert "MOBI6-BODY-MARKER" in html
    assert "data:image/png;base64," in html
    assert 'alt="cover"' in html
    assert html.count("<img") == 1  # 定位不到的那张只剩文字
    assert "filepos" not in html
    assert "mbp:" not in html


def test_parse_mobi6_title_falls_back_to_first_short_block(tmp_path):
    """MOBI 6 没有标题标签：开头第一个短段落当章节名，长段落则不给标题。"""
    text = (
        "<p><font size='7'>第一小节</font></p><p>正文甲</p>"
        "<mbp:pagebreak/>"
        "<p>这一段一上来就是很长的正文说明，明显不是标题，所以不该被当成章节名来用，"
        "再补几句让它彻底超过长度上限：春天的花园里，爱丽丝又一次掉进了兔子洞。</p>"
    ).encode("utf-8")
    book = _parse(_write(tmp_path, "titles.mobi", _book(text)))
    assert book.chapter_count == 2
    assert book.chapters[0].title == "第一小节"
    assert book.chapters[1].title == ""


def test_parse_decodes_cp1252_text(tmp_path):
    path = _write(
        tmp_path,
        "latin.mobi",
        _book("<p>caf\xe9 na\xefve</p>".encode("cp1252"), encoding=1252, title="Latin"),
    )
    assert "café naïve" in _all_html(_parse(path))


def test_parse_plain_palmdoc_without_mobi_header(tmp_path):
    """老式 TEXtREAd：没有 MOBI 头、不压缩，正文是纯文本。

    契约里解析器只认 .azw3 / .mobi，所以这里显式指定扩展名（.prc 不认领）。
    """
    path = _write(
        tmp_path,
        "plain.prc",
        _book("纯文本第一段\n\n纯文本第二段".encode("utf-8"), compression=1, kind=b"TEXtREAd"),
    )
    assert find_handler(".prc") is not None  # 预览走兜底提示页
    assert book_registry.get("mobi").matches(".prc") is False
    book = _parse(path, ext=".mobi")
    assert book.chapter_count == 1
    assert "纯文本第一段" in book.chapters[0].html
    assert "纯文本第二段" in book.chapters[0].text


def test_parse_prefers_kf8_section_of_dual_book(tmp_path):
    """双段文件（MOBI 6 + BOUNDARY + KF8）：优先解析 KF8 段。"""
    mobi6_text = _palmdoc_literals("<p>MOBI6-ONLY-TEXT</p>".encode("utf-8"))
    kf8_text = _palmdoc_literals("<p>KF8-ONLY-TEXT</p>".encode("utf-8"))
    mobi6_record0 = _record0(1, file_version=6, title="旧书名", author="旧作者")
    kf8_record0 = _record0(1, file_version=8, mobi_type=248, title="新书名", author="新作者")
    boundary = b"BOUNDARY" + b"\x00" * 8 + kf8_record0
    path = _write(tmp_path, "dual.azw3", _pdb([mobi6_record0, mobi6_text, boundary, kf8_text]))

    book = _parse(path)
    html = _all_html(book)
    assert "KF8-ONLY-TEXT" in html
    assert "MOBI6-ONLY-TEXT" not in html
    assert book.title == "新书名" and book.author == "新作者"


def test_parse_falls_back_to_mobi6_when_kf8_is_broken(tmp_path):
    """BOUNDARY 里的第二段结构不对时，退回前一段而不是整本失败。"""
    mobi6_text = _palmdoc_literals("<p>MOBI6-ONLY-TEXT</p>".encode("utf-8"))
    mobi6_record0 = _record0(1, file_version=6, title="旧书名", author="旧作者")
    broken_boundary = b"BOUNDARY" + b"\x00" * 8 + b"garbage-not-a-mobi-header"
    path = _write(tmp_path, "broken-kf8.azw3", _pdb([mobi6_record0, mobi6_text, broken_boundary]))

    book = _parse(path)
    assert "MOBI6-ONLY-TEXT" in _all_html(book)
    assert book.title == "旧书名"


# ---------------- 解析层：降级与上限 ----------------


@pytest.mark.parametrize("kwargs", [{"encryption": 2}, {"drm_count": 3}])
def test_parse_drm_raises_book_error(tmp_path, kwargs):
    path = _write(tmp_path, "drm.mobi", _book(b"<p>secret</p>", **kwargs))
    with pytest.raises(BookError) as info:
        _parse(path)
    assert info.value.drm is True
    assert "DRM" in info.value.message
    assert "无法在线预览" in info.value.message


def test_parse_huffcdic_without_tables_degrades(tmp_path):
    """compression=17480 但没有 HUFF/CDIC 表：抛 BookError（不是 DRM），不能崩。"""
    path = _write(
        tmp_path,
        "huff.azw3",
        _book(b"whatever", compression=_HUFF, text_records=[b"\x00\x01\x02"], file_version=8),
    )
    with pytest.raises(BookError) as info:
        _parse(path)
    assert info.value.drm is False
    assert "HUFF/CDIC" in info.value.message
    assert "暂不支持在线预览" in info.value.message


def test_parse_huffcdic_with_broken_tables_degrades(tmp_path):
    path = _write(
        tmp_path,
        "bad-huff.azw3",
        _book(
            b"whatever",
            compression=_HUFF,
            text_records=[b"\x00\x01\x02"],
            extra_records=[b"HUFF\x00\x00\x00\x18broken", b"CDIC\x00\x00\x00\x10broken"],
            huff=(2, 1, 3, 1),
            file_version=8,
        ),
    )
    with pytest.raises(BookError) as info:
        _parse(path)
    assert "HUFF/CDIC" in info.value.message
    assert info.value.drm is False


def test_parse_truncates_oversized_content(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.services.books.mobi.MobiParser.max_text_bytes", 256)
    text = ("<p>" + "长" * 2000 + "</p>").encode("utf-8")
    path = _write(tmp_path, "big.azw3", _book(text, file_version=8, title="大书"))

    book = _parse(path)
    assert book.truncated is True
    assert book.chapter_count >= 1
    assert book.char_count < 2000  # 明显被截断


def test_parse_strips_extra_record_data(tmp_path):
    """extra record data flags=0x03：记录尾部的 TBS 与多字节重叠字节要先剥掉。"""
    text = "<p>CLEAN-PAYLOAD-MARKER</p>".encode("utf-8")
    suffix = b"TBSXYZ" + bytes([0x80 | 7]) + b"\xe4\xb8" + bytes([0x80 | 3])
    path = _write(
        tmp_path,
        "extra.azw3",
        _book(text, extra_data_flags=0x03, extra_suffix=suffix, file_version=8),
    )
    html = _all_html(_parse(path))
    assert "CLEAN-PAYLOAD-MARKER" in html
    assert "TBSXYZ" not in html


def test_parse_broken_files_raise_book_error(tmp_path):
    good = _book(KF8_TEXT, file_version=8)
    cases = {
        "empty.mobi": b"",
        "random.azw3": b"\x00\x01\x02\x03" * 40,
        "magic-only.mobi": b"BOOKMOBI" + b"\x00" * 70,
        "no-records.mobi": _pdb([], name="empty"),
        "no-text.azw3": _pdb([_record0(0, file_version=8)]),  # 只有记录 0
        "truncated.azw3": good[: len(good) // 3],  # 记录表指向文件外
        "half-header.mobi": good[:80],
    }
    for name, data in cases.items():
        path = _write(tmp_path, name, data)
        with pytest.raises(BookError) as info:
            _parse(path)
        assert info.value.message, name
        assert info.value.drm is False, name


# ---------------- HUFF/CDIC ----------------


def _bitstream(codes: list[tuple[int, int]]) -> bytes:
    """把 (码值, 码长) 按 MSB 优先打包成字节流。"""
    bits = "".join(format(value, f"0{length}b") for value, length in codes)
    bits += "0" * ((-len(bits)) % 8)
    return int(bits, 2).to_bytes(len(bits) // 8, "big") if bits else b""


def _cdic_record(entries: list[tuple[bool, bytes]]) -> bytes:
    """CDIC 记录：16 字节头 + 偏移表（相对第 16 字节）+ 词条（长度 | 0x8000 叶子标志）。"""
    count = len(entries)
    bits = max(1, (count - 1).bit_length())
    table_size = count * 2
    body = bytearray()
    offsets = []
    for is_leaf, payload in entries:
        offsets.append(table_size + len(body))
        body += struct.pack(">H", len(payload) | (0x8000 if is_leaf else 0))
        body += payload
    table = b"".join(struct.pack(">H", offset) for offset in offsets)
    return b"CDIC" + struct.pack(">III", 16, count, bits) + table + bytes(body)


def _huff_identity() -> tuple[bytes, bytes]:
    """8 位定长码的 identity 表：压缩流与明文逐字节相同，但走完整的 HUFF/CDIC 路径。"""
    huff = bytearray(24)
    huff[0:8] = b"HUFF\x00\x00\x00\x18"
    struct.pack_into(">II", huff, 8, 24, 24 + 256 * 4)
    for _ in range(256):
        huff += ((255 << 8) | 0x80 | 8).to_bytes(4, "big")  # 码长 8、终结、下标 = 255 - 码值
    huff += bytes(32 * 8)  # dict2 用不到，留空表
    cdic = _cdic_record([(True, bytes([255 - index])) for index in range(256)])
    return bytes(huff), cdic


def _huff_mixed() -> tuple[bytes, bytes]:
    """混合码长表：8 位终结码 + 9 位码（dict2 路径）+ 一个需要递归解包的词条。

    9 位码的头 8 位必须是 0x00（dict1[0x00] 是非终结项），码值取别的值会让头 8 位
    落到终结项上，所以这里只用 0x00 前缀下的两个码。
    """
    huff = bytearray(24)
    huff[0:8] = b"HUFF\x00\x00\x00\x18"
    struct.pack_into(">II", huff, 8, 24, 24 + 256 * 4)
    for prefix in range(256):
        if prefix == 0x00:
            huff += (9).to_bytes(4, "big")  # 非终结项：码长 > 8，真实码长看 dict2
        else:
            huff += ((prefix << 8) | 0x80 | 8).to_bytes(4, "big")  # 终结的 8 位码
    for length in range(1, 33):
        low, high = (0, 2) if length == 9 else (0, 0)
        huff += struct.pack(">II", low, high)
    # 下标 0='A'（8 位码 0xFF）、1='B'（9 位码值 1）、2=节点（内容是编码后的 "BB"）
    node = _bitstream([(1, 9), (1, 9)])
    cdic = _cdic_record([(True, b"A"), (True, b"B"), (False, node)])
    return bytes(huff), cdic


def test_huffcdic_reader_decodes_identity_stream():
    huff, cdic = _huff_identity()
    reader = HuffCdicReader([huff], [cdic])
    payload = b"<p>identity</p>"
    assert reader.unpack(payload, 1 << 20) == payload


def test_parse_huffcdic_identity_tables(tmp_path):
    """有完整 HUFF/CDIC 表时要正常解出正文（而不是走"暂不支持"）。"""
    huff, cdic = _huff_identity()
    text = "<p>HUFFCDIC-BODY-MARKER</p>".encode("utf-8")
    path = _write(
        tmp_path,
        "huff-ok.azw3",
        _book(
            text,
            compression=_HUFF,
            text_records=[text],  # identity 表：压缩流 = 明文
            extra_records=[huff, cdic],
            huff=(2, 1, 3, 1),
            file_version=8,
        ),
    )
    book = _parse(path)
    assert "HUFFCDIC-BODY-MARKER" in _all_html(book)
    assert "HUFFCDIC-BODY-MARKER" in book.chapters[0].text


def test_parse_huffcdic_mixed_codes_and_nested_phrase(tmp_path):
    """9 位码（dict2 路径）与需要递归解包的词条都要能还原。"""
    huff, cdic = _huff_mixed()
    # A(8 位) + B(9 位码值 1) + 节点(9 位码值 0 -> "BB") + B(9 位码值 1) = "ABBBB"
    encoded = _bitstream([(0xFF, 8), (1, 9), (0, 9), (1, 9)])
    path = _write(
        tmp_path,
        "huff-mixed.azw3",
        _book(
            b"ABBBB",
            compression=_HUFF,
            text_records=[encoded],
            extra_records=[huff, cdic],
            huff=(2, 1, 3, 1),
            file_version=8,
        ),
    )
    assert "ABBBB" in _all_html(_parse(path))


# ---------------- 展示层（薄壳 + BookPreview） ----------------


def test_preview_renders_book_page(tmp_path):
    path = _write(
        tmp_path,
        "page.azw3",
        _book(KF8_TEXT, file_version=8, title="页面书名", author="页面作者", language="zh"),
    )
    html = _html_of(path)

    assert "页面书名" in html and "页面作者" in html
    assert "KF8-BODY-MARKER" in html and "中文正文" in html
    assert "MOBI" in html.upper()  # 格式标签
    assert "id='mobi-0'" in html and "id='mobi-1'" in html  # 章节锚点
    assert "目录" in html  # 两章以上要画目录
    assert "<script" not in html.lower() and "xss" not in html
    assert "mbp:" not in html


def test_preview_truncation_note(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.services.books.mobi.MobiParser.max_text_bytes", 256)
    text = ("<p>" + "长" * 2000 + "</p>").encode("utf-8")
    html = _html_of(_write(tmp_path, "big.azw3", _book(text, file_version=8)))
    assert "内容过大，仅显示前一部分，完整内容请下载查看" in html


def test_preview_drm_and_huff_message_pages(tmp_path):
    drm = _write(tmp_path, "drm.mobi", _book(b"<p>secret</p>", encryption=2))
    html = _html_of(drm)
    assert "DRM" in html and "无法在线预览" in html
    assert "secret" not in html

    huff = _write(
        tmp_path,
        "huff.azw3",
        _book(b"whatever", compression=_HUFF, text_records=[b"\x00\x01\x02"], file_version=8),
    )
    html = _html_of(huff)
    assert "HUFF/CDIC" in html and "暂不支持在线预览" in html

    broken = _write(tmp_path, "broken.mobi", b"not a mobi at all")
    html = _html_of(broken)
    assert "打不开这本书" in html


def test_preview_azw3_through_api(client, user_headers, tmp_path):
    data = _book(KF8_TEXT, file_version=8, title="接口书名", author="接口作者")
    upload = client.post(
        "/api/v1/files/upload",
        files={"file": ("api-book.azw3", data, "application/octet-stream")},
        headers=user_headers,
    )
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["id"]

    response = client.get(f"/api/v1/files/{file_id}/preview", headers=user_headers)
    assert response.status_code == 200, response.text
    assert "KF8-BODY-MARKER" in response.text
    assert "接口书名" in response.text
    assert "default-src 'none'" in response.headers["content-security-policy"]

    legacy = client.get(f"/api/v1/files/preview/{file_id}", headers=user_headers)
    assert legacy.status_code == 200


def test_book_json_api_serves_app_clients(client, user_headers):
    """APP 那条线：同一份解析结果直接给 JSON，不经过任何 HTML 外壳。"""
    data = _book(KF8_TEXT, file_version=8, title="接口书名", author="接口作者", language="zh")
    upload = client.post(
        "/api/v1/files/upload",
        files={"file": ("app-book.azw3", data, "application/octet-stream")},
        headers=user_headers,
    )
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["id"]

    response = client.get(f"/api/v1/files/{file_id}/book", headers=user_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["format"] == "mobi"
    assert payload["title"] == "接口书名"
    assert payload["author"] == "接口作者"
    assert payload["language"] == "zh"
    assert payload["chapter_count"] == 2
    assert payload["truncated"] is False
    assert len(payload["chapters"]) == 2
    assert payload["chapters"][0]["anchor"] == "mobi-0"
    assert "KF8-BODY-MARKER" in payload["chapters"][0]["html"]
    assert "KF8-BODY-MARKER" in payload["chapters"][0]["text"]
    assert "<script" not in payload["chapters"][0]["html"].lower()
    assert payload["file_id"] == file_id and payload["download_url"]

    # 只要某一节、且不要 html/text 时不应该白传正文
    only = client.get(
        f"/api/v1/files/{file_id}/book",
        params={"chapter": 1, "html": "false", "text": "false"},
        headers=user_headers,
    )
    assert only.status_code == 200, only.text
    assert len(only.json()["chapters"]) == 1
    assert "html" not in only.json()["chapters"][0]
    assert "text" not in only.json()["chapters"][0]


# ---------------- 真实样本（存在才跑） ----------------


@pytest.mark.skipif(not REAL_AZW3.exists(), reason="真实 AZW3 样本不存在")
def test_real_azw3_sample():
    book = _parse(REAL_AZW3)
    html = _all_html(book)
    assert book.format == "mobi"
    assert book.title == "Alice's Adventures in Wonderland"
    assert book.author == "Lewis Carroll"
    # KF8 用 <div class="chapter"> 分章：front matter + 12 章
    assert book.chapter_count == 13
    assert book.chapters[1].title.startswith("CHAPTER I.")
    assert book.char_count > 100_000
    assert "Wonderland" in html
    assert "<script" not in html.lower()

    preview = _html_of(REAL_AZW3)
    assert "Alice" in preview and "Lewis Carroll" in preview
    assert "目录" in preview  # 有目录了（此前整本挤在一章里）


@pytest.mark.skipif(not REAL_MOBI.exists(), reason="真实 MOBI 样本不存在")
def test_real_mobi_sample():
    book = _parse(REAL_MOBI)
    html = _all_html(book)
    assert book.format == "mobi"
    assert book.title == "Alice's Adventures in Wonderland"
    assert book.author == "Lewis Carroll"
    assert book.chapter_count > 10  # <mbp:pagebreak/> 切章
    assert all(chapter.anchor.startswith("mobi-") for chapter in book.chapters)
    assert any(chapter.title.startswith("CHAPTER I.") for chapter in book.chapters)
    assert "Wonderland" in html
    assert "mbp:" not in html
    assert "filepos" not in html

    preview = _html_of(REAL_MOBI)
    assert "Alice" in preview and "目录" in preview
