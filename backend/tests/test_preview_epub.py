"""EPUB 的解析层（纯数据）与预览层（网页）测试。

样本全部在测试里用 ``zipfile`` 现场生成，仓库里不放二进制文件。

分两段：

- **解析层**：``backend.services.books.epub`` → :func:`parse_book` 产出的
  :class:`Book`（元数据 / 章节 / 纯文本 / 图片内联 / 上限 / 报错），
  这一层手机 APP 也要用，所以断言都打在数据上
- **展示层**：``backend.extensions.preview.epub`` 把 Book 画成网页
  （目录锚点、正文、错误提示页、HTTP 端到端）

本机若有 /tmp/books/alice.epub（真实 EPUB），两段各自再加一遍真实文件验证。
"""

from __future__ import annotations

import base64
import io
import re
import struct
import zipfile
import zlib
from pathlib import Path

import pytest

from backend.extensions.preview import find_handler, render_preview, supported_extensions
from backend.extensions.preview.epub import EpubPreview
from backend.services.books import BookError, clear_cache, parse_book, registry
from backend.services.books.epub import EpubParser

# ---------------- 样本构造（现场生成） ----------------

_CONTAINER_XML = """<?xml version="1.0" encoding="utf-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

_ENCRYPTION_XML = """<?xml version="1.0" encoding="utf-8"?>
<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <EncryptedData xmlns="http://www.w3.org/2001/04/xmlenc#"/>
</encryption>
"""

#: 故意夹带私货的一章：脚本、onerror、javascript: 链接、外链、@import、url()
_CHAPTER_1 = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>第一章</title>
  <style>
    p { color: #333; font-size: 120%; }
    @import url("http://evil.example/x.css");
    body { background-image: url(javascript:alert(1)); }
  </style>
</head>
<body>
  <h1>第一章 开始</h1>
  <p>第一章的正文。</p>
  <script>alert('xss')</script>
  <img src="missing.png" onerror="alert(1)">
  <p><a href="ch2.xhtml#note">跳到第二章</a></p>
  <p><a href="javascript:alert(2)">危险链接</a><a href="https://example.com/">外部链接</a></p>
  <figure><img src="Images/pixel.png" alt="小图"/></figure>
</body>
</html>
"""

_CHAPTER_2 = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>第二章</title></head>
<body>
  <h2>第二章 结束</h2>
  <p>第二章的正文。</p>
</body>
</html>
"""

#: 没有 h1~h3 的一章：标题应该退回文件名
_CHAPTER_NO_HEADING = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body><p>没有标题的正文。</p></body>
</html>
"""

#: 畸形到 XML 解析器吃不下的章节：<p> 不闭合 + &nbsp; + 未自闭合的 <br>
_CHAPTER_MALFORMED = """<html xmlns="http://www.w3.org/1999/xhtml"><head>
  <style>p { text-indent: 1em; }</style></head>
<body><h2>畸形章节</h2><p>第一段没闭合<p>第二段&nbsp;内容<br>
<script>alert('xss')</script><img src="Images/pixel.png" alt="图"></body></html>
"""


def _png_bytes() -> bytes:
    """现场生成一张 2x2 的 PNG（几十字节，用来验证 base64 内联）。"""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)  # 2x2、8bit 真彩色
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * 2 for _ in range(2))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _opf_xml(
    items: list[tuple[str, str, str]],
    *,
    spine: list[str] | None = None,
    title: str = "测试书",
    creator: str = "作者甲",
    language: str = "zh-CN",
) -> str:
    """按 (id, href, media-type) 列表拼一份 OPF。"""
    manifest = "".join(
        f'<item id="{item_id}" href="{href}" media-type="{media}"/>'
        for item_id, href, media in items
    )
    refs = "".join(
        f'<itemref idref="{item_id}"/>' for item_id in (spine or [i for i, _, _ in items])
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{title}</dc:title>
    <dc:creator>{creator}</dc:creator>
    <dc:language>{language}</dc:language>
  </metadata>
  <manifest>{manifest}</manifest>
  <spine>{refs}</spine>
</package>"""


_DEFAULT_ITEMS = [
    ("ch1", "ch1.xhtml", "application/xhtml+xml"),
    ("ch2", "ch2.xhtml", "application/xhtml+xml"),
    ("pixel", "Images/pixel.png", "image/png"),
]
_DEFAULT_OPF = _opf_xml(_DEFAULT_ITEMS)
_DEFAULT_FILES = {
    "OEBPS/ch1.xhtml": _CHAPTER_1.encode(),
    "OEBPS/ch2.xhtml": _CHAPTER_2.encode(),
    "OEBPS/Images/pixel.png": _png_bytes(),
}


def _epub_bytes(
    *,
    encryption: bool = False,
    container_xml: str | None = _CONTAINER_XML,
    opf_xml: str | None = _DEFAULT_OPF,
    files: dict[str, bytes] | None = None,
) -> bytes:
    """现场造一本 EPUB 并返回字节。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        if container_xml is not None:
            archive.writestr("META-INF/container.xml", container_xml)
        if encryption:
            archive.writestr("META-INF/encryption.xml", _ENCRYPTION_XML)
        if opf_xml is not None:
            archive.writestr("OEBPS/content.opf", opf_xml)
        for name, data in (_DEFAULT_FILES if files is None else files).items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _write_epub(tmp_path: Path, **kwargs) -> Path:
    """落盘并清掉解析缓存（同一个路径反复用时缓存会挡住新内容）。"""
    target = tmp_path / "book.epub"
    target.write_bytes(_epub_bytes(**kwargs))
    clear_cache()
    return target


@pytest.fixture
def book(tmp_path):
    """直接走解析层，拿 :class:`Book`。"""

    def _book(**kwargs):
        return parse_book(_write_epub(tmp_path, **kwargs))

    return _book


@pytest.fixture
def render(tmp_path):
    """走展示层（预览扩展），拿渲染好的 HTML 字符串。"""

    def _render(**kwargs) -> str:
        preview = EpubPreview().render(_write_epub(tmp_path, **kwargs))
        assert preview.kind == "html", preview
        return preview.html or ""

    return _render


def _has_attr(html: str, attr: str, value: str) -> bool:
    """属性断言（展示层用单引号、解析层用双引号，测试不该绑死引号风格）。"""
    return re.search(rf"""{attr}=['"]{re.escape(value)}['"]""", html) is not None


# ================= 解析层：Book 数据 =================


def test_parse_book_reads_metadata_and_chapters(book):
    parsed = book()

    assert parsed.format == "epub"
    assert parsed.title == "测试书"
    assert parsed.author == "作者甲"
    assert parsed.language == "zh-CN"
    assert parsed.chapter_count == 2
    assert parsed.truncated is False
    assert parsed.note == ""

    # 锚点由解析层统一分配，全局唯一
    assert [chapter.anchor for chapter in parsed.chapters] == ["epub-0", "epub-1"]
    assert [chapter.index for chapter in parsed.chapters] == [0, 1]
    assert parsed.chapters[0].title == "第一章 开始"
    assert parsed.chapters[1].title == "第二章 结束"


def test_parse_book_keeps_plain_text_for_native_clients(book):
    parsed = book()

    text = parsed.chapters[0].text
    assert "第一章的正文。" in text
    assert "<" not in text  # text 是纯文本，不是 HTML
    assert parsed.char_count > 0


def test_parse_book_follows_spine_order(tmp_path):
    """spine 决定阅读顺序：倒过来写，章节也要跟着倒。"""
    opf = _opf_xml(_DEFAULT_ITEMS, spine=["ch2", "ch1"])
    parsed = parse_book(_write_epub(tmp_path, opf_xml=opf))

    assert [chapter.anchor for chapter in parsed.chapters] == ["epub-0", "epub-1"]
    assert "第二章的正文。" in parsed.chapters[0].text
    assert "第一章的正文。" in parsed.chapters[1].text


def test_parse_book_uses_filename_when_chapter_has_no_heading(tmp_path):
    opf = _opf_xml([("plain", "plain.xhtml", "application/xhtml+xml")], title="无标题书")
    parsed = parse_book(
        _write_epub(
            tmp_path,
            opf_xml=opf,
            files={"OEBPS/plain.xhtml": _CHAPTER_NO_HEADING.encode()},
        )
    )

    assert parsed.title == "无标题书"
    assert parsed.chapters[0].title == "plain.xhtml"  # 标题兜底用文件名
    assert "没有标题的正文。" in parsed.chapters[0].text


def test_parse_book_inlines_images_as_data_uri(book):
    html = book().chapters[0].html

    match = re.search(r'src="data:image/png;base64,([A-Za-z0-9+/=]+)"', html)
    assert match, "章节里的 PNG 应该被内联成 data: URI"
    assert base64.b64decode(match.group(1)) == _png_bytes()

    # 找不到的图片留占位说明，而不是留下会让客户端去请求的相对路径
    assert '<span class="book-img-note">[图片未内联' in html
    assert 'src="missing.png"' not in html


def test_parse_book_sanitizes_chapter_html(book):
    html = book().chapters[0].html
    lowered = html.lower()

    assert "<script" not in lowered
    assert "alert('xss')" not in html  # 脚本内容也不能当正文漏出来
    assert "onerror" not in lowered
    assert "javascript:" not in lowered
    assert "evil.example" not in lowered  # @import / url() 交给共用清洗器丢掉
    assert "<style" not in lowered  # 书籍 CSS 不进来，排版归展示层


def test_chapter_html_carries_no_page_shell(book):
    """解析层只出数据：HTML 外壳、样式、页面文案都不该出现。"""
    parsed = book()
    html = "".join(chapter.html for chapter in parsed.chapters)

    assert "<!doctype" not in html.lower()
    assert "<style" not in html.lower()
    assert "仅显示前一部分" not in html
    assert "仅显示前一部分" not in parsed.note


def test_parse_book_rewrites_internal_links(book):
    html = book().chapters[0].html

    assert _has_attr(html, "href", "#epub-1")  # 书内相对链接 → 章节锚点
    assert "ch2.xhtml" not in html
    assert "跳到第二章" in html

    # 外链去掉 href，文字保留、原地址写进 title
    assert "外部链接" in html
    assert not _has_attr(html, "href", "https://example.com/")
    assert _has_attr(html, "title", "https://example.com/")

    # javascript: 链接只留文字，且不回显脚本地址
    assert "危险链接" in html
    assert "javascript" not in html.lower()


def test_parse_book_handles_malformed_xhtml(tmp_path):
    """XHTML 畸形时退回整段清洗：正文还在，脚本与相对路径不能漏。"""
    opf = _opf_xml([("bad", "bad.xhtml", "application/xhtml+xml")], title="畸形书")
    parsed = parse_book(
        _write_epub(
            tmp_path,
            opf_xml=opf,
            files={"OEBPS/bad.xhtml": _CHAPTER_MALFORMED.encode()},
        )
    )

    chapter = parsed.chapters[0]
    assert parsed.title == "畸形书"
    assert chapter.title == "畸形章节"  # 标题仍能从章内取出来
    assert "第一段没闭合" in chapter.html
    assert "第二段" in chapter.html
    assert "<script" not in chapter.html.lower()
    assert "xss" not in chapter.html.lower()
    assert '<span class="book-img-note">[图片未内联' in chapter.html
    assert "text-indent" not in chapter.html  # 退路同样不留 CSS


def test_parse_book_truncates_over_max_chapters(tmp_path, monkeypatch):
    monkeypatch.setattr(EpubParser, "max_chapters", 1)
    parsed = parse_book(_write_epub(tmp_path))

    assert parsed.truncated is True
    assert parsed.chapter_count == 1
    assert "第一章的正文。" in parsed.chapters[0].text


def test_parse_book_truncates_over_max_html_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(EpubParser, "max_html_bytes", 200)
    parsed = parse_book(_write_epub(tmp_path))

    assert parsed.truncated is True
    assert parsed.chapter_count == 1  # 至少留第一章，后面的截掉
    assert "第一章的正文。" in parsed.chapters[0].text


def test_parse_book_notes_missing_chapters(tmp_path):
    """spine 里声明了、zip 里却没有的章节：跳过并把数量写进 note。"""
    opf = _opf_xml(_DEFAULT_ITEMS, spine=["ch1", "ch2"])
    parsed = parse_book(
        _write_epub(tmp_path, opf_xml=opf, files={"OEBPS/ch1.xhtml": _CHAPTER_1.encode()})
    )

    assert parsed.chapter_count == 1
    assert "1 章内容缺失" in parsed.note


def test_parse_book_raises_for_drm(book):
    with pytest.raises(BookError) as excinfo:
        book(encryption=True)

    assert excinfo.value.drm is True
    assert "DRM" in excinfo.value.message
    assert "加密" in excinfo.value.message


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"container_xml": None}, id="没有 container.xml"),
        pytest.param({"container_xml": "<container>这不是 XML"}, id="container.xml 坏了"),
        pytest.param({"opf_xml": None}, id="OPF 不存在"),
        pytest.param(
            {"opf_xml": "<?xml version='1.0'?><package><manifest>"}, id="OPF 解析失败"
        ),
    ],
)
def test_parse_book_raises_for_broken_books(book, kwargs):
    with pytest.raises(BookError) as excinfo:
        book(**kwargs)

    assert excinfo.value.drm is False
    assert "无法解析这本 EPUB" in excinfo.value.message


def test_parse_book_raises_for_non_zip_file(tmp_path):
    target = tmp_path / "fake.epub"
    target.write_bytes("这根本不是 zip".encode())
    clear_cache()

    with pytest.raises(BookError) as excinfo:
        parse_book(target)

    assert "无法解析这本 EPUB" in excinfo.value.message


def test_epub_parser_is_registered_as_a_book_parser():
    from backend.services.books import BookParser, find_parser, supported_extensions

    parser = find_parser(".epub")
    assert isinstance(parser, BookParser)
    assert parser.name == "epub"
    assert "epub" in registry.names
    assert ".epub" in supported_extensions()


def test_parse_layer_has_no_web_dependencies():
    """解析层要能独立给 APP 用：不许 import FastAPI，也不许碰预览扩展。

    （``backend.extensions.registry`` 只是可拆卸注册表，官方约定里允许用。）
    """
    package = Path(__import__("backend.services.books.epub", fromlist=["x"]).__file__).parent
    forbidden = (
        "import fastapi",
        "from fastapi",
        "import backend.extensions.preview",
        "from backend.extensions.preview",
    )
    for source_file in sorted(package.glob("*.py")):
        for line in source_file.read_text(encoding="utf-8").splitlines():
            assert not line.strip().startswith(forbidden), f"{source_file.name}: {line.strip()}"


# ================= 展示层：网页预览 =================


def test_preview_handler_is_registered_ahead_of_the_fallback():
    handler = find_handler(".epub")
    assert isinstance(handler, EpubPreview)
    # 必须比 text（10）更靠前，更不能被兜底扩展（-100）抢走
    assert handler.priority > 10
    assert ".epub" in supported_extensions()


def test_preview_is_reachable_through_the_registry(tmp_path):
    preview = render_preview(_write_epub(tmp_path), ".epub")

    assert preview is not None
    assert preview.kind == "html"
    assert "第一章的正文。" in (preview.html or "")


def test_preview_renders_metadata_toc_and_chapters(render):
    html = render()

    assert "测试书" in html  # 书名
    assert "作者甲" in html  # 作者
    assert "2 节" in html  # 章节数
    assert "第一章的正文。" in html
    assert "第二章的正文。" in html

    # 目录 + 章节标题各出现一次
    assert html.count("第一章 开始") == 2
    assert _has_attr(html, "id", "epub-0") and _has_attr(html, "id", "epub-1")
    assert _has_attr(html, "href", "#epub-0") and _has_attr(html, "href", "#epub-1")


def test_preview_keeps_scripts_and_events_out(render):
    html = render()
    lowered = html.lower()

    assert "<script" not in lowered
    assert "alert('xss')" not in html
    assert "onerror" not in lowered
    assert "javascript:" not in lowered
    assert "evil.example" not in lowered


def test_preview_inlines_images_and_marks_the_rest(render):
    html = render()

    assert "data:image/png;base64," in html
    assert '<span class="book-img-note">[图片未内联' in html
    assert 'src="missing.png"' not in html


def test_preview_reports_drm(render):
    html = render(encryption=True)

    assert "DRM" in html
    assert "加密" in html
    assert "第一章的正文。" not in html


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"container_xml": None}, id="没有 container.xml"),
        pytest.param({"container_xml": "<container>这不是 XML"}, id="container.xml 坏了"),
        pytest.param({"opf_xml": None}, id="OPF 不存在"),
        pytest.param(
            {"opf_xml": "<?xml version='1.0'?><package><manifest>"}, id="OPF 解析失败"
        ),
    ],
)
def test_preview_reports_broken_books(render, kwargs):
    html = render(**kwargs)

    assert "无法解析这本 EPUB" in html
    assert "第一章的正文。" not in html


def test_preview_never_raises_for_a_non_zip_file(tmp_path):
    target = tmp_path / "fake.epub"
    target.write_bytes("这根本不是 zip".encode())
    clear_cache()

    preview = EpubPreview().render(target)

    assert preview.kind == "html"
    assert "无法解析这本 EPUB" in (preview.html or "")


def test_preview_shows_truncation_note(tmp_path, monkeypatch):
    """截断的提示文案由展示层写，解析层只置 truncated。"""
    monkeypatch.setattr(EpubParser, "max_chapters", 1)
    html = EpubPreview().render(_write_epub(tmp_path)).html or ""

    assert "内容过大" in html
    assert "第一章的正文。" in html
    assert "第二章的正文。" not in html


# ================= 真实 EPUB + 端到端 =================

_REAL_BOOK = Path("/tmp/books/alice.epub")
_needs_real_book = pytest.mark.skipif(not _REAL_BOOK.exists(), reason="本机没有真实 EPUB 样本")


@_needs_real_book
def test_real_book_parses_into_a_book():
    parsed = parse_book(_REAL_BOOK)

    assert parsed.format == "epub"
    assert parsed.title.startswith("Alice")
    assert parsed.author == "Lewis Carroll"
    assert parsed.language == "en"
    assert parsed.chapter_count >= 10
    assert parsed.truncated is False
    assert parsed.char_count > 50_000
    assert parsed.chapters[0].anchor == "epub-0"

    text = "".join(chapter.text for chapter in parsed.chapters)
    assert "Alice was beginning to get very tired" in text
    assert "<" not in text  # 纯文本里不该有标签


@_needs_real_book
def test_real_book_preview_renders():
    preview = EpubPreview().render(_REAL_BOOK)

    assert preview.kind == "html"
    html = preview.html or ""
    assert "Alice" in html and "Carroll" in html
    assert "Down the Rabbit-Hole" in html
    assert "Alice was beginning to get very tired" in html
    assert "data:image/jpeg;base64," in html  # 封面图内联

    anchors = re.findall(r"""id=['"](epub-\d+)['"]""", html)
    assert len(anchors) >= 10
    assert _has_attr(html, "href", f"#{anchors[0]}")
    assert "<script" not in html.lower()
    assert "onerror" not in html.lower()


@_needs_real_book
def test_real_book_end_to_end(client, user_headers):
    """真实 EPUB 走一遍 HTTP：上传 → /api/v1/files/{id}/preview。"""
    upload = client.post(
        "/api/v1/files/upload",
        files={"file": ("alice.epub", _REAL_BOOK.read_bytes(), "application/epub+zip")},
        headers=user_headers,
    )
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["id"]

    response = client.get(f"/api/v1/files/{file_id}/preview", headers=user_headers)
    assert response.status_code == 200, response.text
    assert "Carroll" in response.text
    assert "Down the Rabbit-Hole" in response.text
    assert "data:image/jpeg;base64," in response.text
    assert "<script" not in response.text.lower()
    assert "default-src 'none'" in response.headers["content-security-policy"]


def test_preview_end_to_end(client, user_headers):
    """合成样本走一遍上传 → 预览接口，确认接口层能正常返回 HTML。"""
    upload = client.post(
        "/api/v1/files/upload",
        files={"file": ("epub-test.epub", _epub_bytes(), "application/epub+zip")},
        headers=user_headers,
    )
    if upload.status_code == 400 and "不支持的文件类型" in upload.text:
        pytest.skip("上传白名单还没放行 .epub")
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["id"]

    response = client.get(f"/api/v1/files/{file_id}/preview", headers=user_headers)
    assert response.status_code == 200, response.text
    assert "测试书" in response.text
    assert "第一章的正文。" in response.text
    assert "data:image/png;base64," in response.text
    assert "default-src 'none'" in response.headers["content-security-policy"]

    # 旧前端路径同样可用
    legacy = client.get(f"/api/v1/files/preview/{file_id}", headers=user_headers)
    assert legacy.status_code == 200
    assert "第二章的正文。" in legacy.text
