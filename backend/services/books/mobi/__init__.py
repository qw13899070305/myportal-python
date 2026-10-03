"""Kindle 电子书（.azw3 / .mobi）解析器 —— 纯数据层。

流水线：PalmDB 容器 -> PalmDOC / MOBI 头（含 KF8 双段）-> EXTH 元数据
-> 正文解压（原样 / PalmDOC LZ77 / HUFF-CDIC）-> 清洗分章 -> :class:`Book`。

本包**只产出数据**：没有 HTML 外壳、CSS、按钮文案，也不认识 ``Preview``
与 FastAPI。网页预览在 ``extensions/preview/mobi.py``（薄壳 + 共用展示层），
手机 APP 直接消费 ``GET /api/v1/files/{id}/book`` 的 JSON。

模块分工
--------
``pdb``       PalmDB 头与记录表（每项先偏移后属性）
``header``    PalmDOC / MOBI / EXTH 头部与 KF8 分段
``palmdoc``   PalmDOC LZ77 解压
``huffcdic``  HUFF/CDIC 解压
``markup``    正文标记 → 清洗后的 HTML 片段（图片内联、分章）
``errors``    层内异常（由本模块翻译成 :class:`BookError`）
"""

from __future__ import annotations

from pathlib import Path

from backend.core.logger import logger
from backend.extensions.registry import get_registry
from backend.services.books import Book, BookError, BookParser, Chapter
from backend.services.books.mobi import header as mobi_header
from backend.services.books.mobi.errors import DrmProtected, MobiFormatError, UnsupportedFeature
from backend.services.books.mobi.huffcdic import HuffCdicReader, looks_like_text
from backend.services.books.mobi.markup import (
    chapter_title,
    fragment_to_html,
    image_inliner,
    split_chapters,
)
from backend.services.books.mobi.palmdoc import decompress as palmdoc_decompress
from backend.services.books.mobi.pdb import PalmDatabase
from backend.services.books.sanitize import strip_tags


class MobiParser(BookParser):
    """AZW3（KF8）/ MOBI 6 解析器。"""

    name = "mobi"
    extensions = frozenset({".azw3", ".mobi"})
    priority = 20

    #: 解压后的正文上限，超出就截断并置 ``Book.truncated``
    max_text_bytes = 2 * 1024 * 1024
    #: 单张内联图片上限
    max_image_bytes = 2 * 1024 * 1024
    #: 磁盘文件上限，避免把几百 MB 的文件整个读进内存
    max_file_bytes = 64 * 1024 * 1024

    def parse(self, path: Path) -> Book:
        """解析成 :class:`Book`；失败抛 :class:`BookError`（用户可见的中文说明）。"""
        try:
            return self._parse(path)
        except DrmProtected as exc:
            logger.info(f"MOBI 解析遇到 DRM（{path.name}）：{exc}")
            raise BookError(
                "这本书有 DRM 保护，无法在线预览，请用已授权的阅读器打开", drm=True
            ) from exc
        except UnsupportedFeature as exc:
            logger.info(f"MOBI 解析降级（{path.name}）：{exc}")
            raise BookError(f"{exc}，暂不支持在线预览，请下载后用阅读器打开") from exc
        except MobiFormatError as exc:
            logger.warning(f"MOBI 解析失败（{path.name}）：{exc}")
            raise BookError("文件结构不完整或格式不受支持，请下载后用阅读器打开") from exc

    # ---------------- 主流程 ----------------

    def _parse(self, path: Path) -> Book:
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise MobiFormatError(f"读不到文件：{exc}") from exc
        if size == 0:
            raise MobiFormatError("文件是空的")
        if size > self.max_file_bytes:
            raise MobiFormatError(f"文件超过 {self.max_file_bytes // (1024 * 1024)}MB")

        database = PalmDatabase(path.read_bytes())
        main = mobi_header.main_section(database)
        kf8 = mobi_header.parse_kf8_section(database)
        # KF8 段有正常 HTML 与 EXTH 书名，优先渲染它；结构不对才退回前一段（MOBI 6）
        sections = [section for section in (kf8, main) if section is not None]
        for section in sections:
            if section.has_drm:
                raise DrmProtected("PalmDOC 加密标志或 MOBI 的 DRM 字段非 0")

        failure: MobiFormatError | None = None
        for section in sections:
            try:
                text, truncated = self._extract_text(database, section)
            except UnsupportedFeature as exc:
                failure = exc
                continue
            if not text.strip():
                continue
            book = self._build_book(database, section, text, truncated)
            if book is not None:
                return book
        if failure is not None:
            raise failure
        raise MobiFormatError("没有解出任何可显示的正文")

    # ---------------- 正文解压 ----------------

    def _extract_text(
        self, database: PalmDatabase, section: mobi_header.Section
    ) -> tuple[bytes, bool]:
        """解压正文，最多 :attr:`max_text_bytes` 字节；返回 (正文, 是否截断)。"""
        compression = section.palmdoc.compression
        if compression not in (1, 2, mobi_header.HUFF_COMPRESSION):
            raise UnsupportedFeature(f"不支持的压缩方式（compression={compression}）")
        extra_flags = section.mobi.extra_data_flags if section.mobi else 0

        chunks: list[bytes] = []
        total = 0
        truncated = False
        huff: HuffCdicReader | None = None
        for index in self._text_range(database, section):
            record = database.record(index)
            if not record:
                continue  # 截断/空记录跳过，别让整本书失败
            payload = mobi_header.strip_trailing_data(record, extra_flags)
            if not payload:
                continue
            room = self.max_text_bytes - total
            if compression == 1:
                piece = payload[:room]
            elif compression == 2:
                piece = palmdoc_decompress(payload, room)
            else:
                if huff is None:
                    huff = self._huff_reader(database, section)
                piece = huff.unpack(payload, room)
            chunks.append(piece)
            total += len(piece)
            if total >= self.max_text_bytes:
                truncated = True
                break

        text = b"".join(chunks)
        if compression == mobi_header.HUFF_COMPRESSION and not looks_like_text(text):
            # 表能建起来但解出来不像正文：多半是表没解对，宁可退回"暂不支持"
            raise UnsupportedFeature("HUFF/CDIC 解压结果异常")
        return text, truncated

    def _text_range(self, database: PalmDatabase, section: mobi_header.Section) -> range:
        """正文记录号区间。

        从记录 1（KF8 段从 BOUNDARY 的下一条）开始取 record_count 条。
        0xB0 的 first_content_record 在实测的 AZW3 里是 0，不能当起点；
        0x40 的 first_non_book_index 可以用来兜住明显过大的 record_count。
        """
        count = section.palmdoc.record_count
        header = section.mobi
        if header is not None and 0 < header.first_non_book_index <= count + 1:
            count = min(count, header.first_non_book_index - 1)
        count = min(count, max(0, len(database) - section.text_start))
        return range(section.text_start, section.text_start + count)

    def _huff_reader(self, database: PalmDatabase, section: mobi_header.Section) -> HuffCdicReader:
        header = section.mobi
        if header is None:
            raise UnsupportedFeature("没有 MOBI 头，定位不到 HUFF/CDIC 表")
        if not 0 < header.huffman_record_count <= 64:
            raise UnsupportedFeature("HUFF/CDIC 表记录缺失")
        if not 0 < header.huffman_table_length <= 4096:
            raise UnsupportedFeature("HUFF/CDIC 表记录缺失")
        huffs = database.record_slice(header.huffman_record_offset, header.huffman_record_count)
        cdics = database.record_slice(header.huffman_table_offset, header.huffman_table_length)
        try:
            return HuffCdicReader(huffs, cdics)
        except MobiFormatError as exc:
            # 细节（越界偏移之类）只写日志：给用户的理由要稳定、看得懂
            logger.debug(f"HUFF/CDIC 建表失败（{section.title}）：{exc}")
            raise UnsupportedFeature("HUFF/CDIC 表结构不合法") from exc

    # ---------------- 组装 Book ----------------

    def _build_book(
        self,
        database: PalmDatabase,
        section: mobi_header.Section,
        text: bytes,
        truncated: bool,
    ) -> Book | None:
        resolve_image = image_inliner(database, section, self.max_image_bytes)
        markup = text.decode(section.encoding, errors="replace")
        chapters: list[Chapter] = []
        for raw in split_chapters(markup):
            html = fragment_to_html(raw, resolve_image)
            plain = strip_tags(html)
            if not plain and "<img" not in html:
                continue  # 切出来的空段（分隔符、只剩标签的占位）直接丢掉
            index = len(chapters)
            chapters.append(
                Chapter(
                    index=index,
                    title=chapter_title(html),
                    html=html,
                    text=plain,
                    anchor=f"mobi-{index}",
                )
            )
        if not chapters:
            return None
        return Book(
            format=self.name,
            title=section.title or database.database_name,
            author=section.author,
            language=section.language,
            chapters=tuple(chapters),
            truncated=truncated,
        )


get_registry("book").register(MobiParser())


__all__ = ["MobiParser"]
