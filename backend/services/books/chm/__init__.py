"""CHM（Windows 帮助文件）解析器——产出纯数据的 :class:`Book`。

CHM 的正文通常是 LZX 压缩的，本包完全自包含（只用标准库 + 共用清洗）：

==============================  ================================================
模块                             职责
==============================  ================================================
``container.py``                ITSF 头 / 文件长度头 / ITSP 目录（PMGL 块）/ 查找
``content.py``                  内容段（NameList、未压缩段、LZX 段、reset table、逐帧取字节）
``errors.py``                   层内异常（由本模块翻译成 ``BookError``）
``lzx/``                        LZX 解码（位读取、Huffman 表、解码主循环）
``textutil.py``                 正文编码猜测、``mk:@MSITStore:`` 之类链接前缀
``topics.py``                   默认主题、.hhc/.hhk 目录树、正文页面筛选排序
``html_page.py``                单个主题页的图片内联与链接重写
==============================  ================================================

这一层**只出数据**：没有 HTML 外壳、没有 CSS、没有按钮提示文案，坏文件一律
``raise BookError("中文说明")``。网页怎么排版是
``backend/extensions/preview/book_base.py`` 的事，APP 直接吃 ``Book`` 的 JSON。
"""

from __future__ import annotations

from pathlib import Path

from backend.core.logger import logger
from backend.extensions.registry import get_registry
from backend.services.books import Book, BookError, BookParser, Chapter

from .container import ChmFile
from .errors import ChmError
from .html_page import PageBuilder, extract_title, looks_like_html
from .lzx import LzxDecoder, LzxError
from .textutil import decode_text, language_tag
from .topics import book_title, build_toc, default_topic, toc_titles, topic_order

_MB = 1024 * 1024


class ChmParser(BookParser):
    """把 .chm 解析成 :class:`Book`（一章 = 一个主题页）。"""

    name = "chm"
    extensions = frozenset({".chm"})
    priority = 20

    #: 单个 CHM 文件大小上限
    max_file_size = 128 * _MB
    #: 最多解析多少个主题页
    max_topics = 300
    #: 全部主题页正文的原始体量上限（第一页无论多大都会保留）
    max_html_bytes = 2 * _MB
    #: 目录条目上限
    max_toc_entries = 300
    #: LZX 解压总量预算（实测约 5MB/s，这里给几秒的额度）
    max_decode_bytes = 24 * _MB

    # ---------------- 入口 ----------------

    def parse(self, path: Path) -> Book:
        chm = self._open(self._read_bytes(path))

        items, toc_truncated = build_toc(chm, self.max_toc_entries)
        order = topic_order(chm, items, default_topic(chm))
        if not order:
            raise BookError("该帮助文件里没有网页正文（.htm/.html），请下载后用本地阅读器打开。")

        included, truncated = self._collect(chm, order)
        if not included:
            raise BookError("无法解压该 CHM 的正文内容，请下载后用本地阅读器打开。")
        truncated = truncated or toc_truncated

        anchors = {name.lower(): f"chm-topic-{index}" for index, (name, _) in enumerate(included)}
        builder = PageBuilder(chm, anchors)
        titles = toc_titles(items)
        chapters: list[Chapter] = []
        for index, (name, raw_text) in enumerate(included):
            html = builder.build(name, raw_text)
            chapters.append(
                Chapter(
                    index=index,
                    # 标题优先级：页面 <title> -> 目录里的名字 -> 文件名
                    title=extract_title(raw_text)
                    or titles.get(name.lower(), "")
                    or name.lstrip("/"),
                    html=html,
                    text=builder.chapter_text(html),
                    anchor=anchors[name.lower()],
                )
            )

        note = ""
        if truncated:
            note = f"该帮助文件共有 {len(order)} 个页面，这里只解析了前 {len(chapters)} 个。"
        logger.debug(
            f"[chm] {path.name}: {len(chapters)} 章 / "
            f"解压 {chm.decoded_bytes} 字节 / 截断={truncated}"
        )
        return Book(
            format=self.name,
            title=book_title(chm) or chapters[0].title or path.name,
            language=language_tag(chm.language),
            chapters=tuple(chapters),
            truncated=truncated,
            note=note,
        )

    # ---------------- 读文件与容错 ----------------

    def _read_bytes(self, path: Path) -> bytes:
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise BookError(f"无法读取文件：{exc}") from exc
        if size == 0:
            raise BookError("文件内容为空。")
        if size > self.max_file_size:
            raise BookError(f"文件超过 {self.max_file_size // _MB}MB，请下载后用本地阅读器打开。")
        try:
            return path.read_bytes()
        except OSError as exc:
            raise BookError(f"无法读取文件：{exc}") from exc

    def _open(self, data: bytes) -> ChmFile:
        try:
            return ChmFile(data)
        except ChmError as exc:
            raise BookError(str(exc)) from exc
        except (LzxError, IndexError, ValueError) as exc:
            logger.warning(f"[chm] 结构解析失败: {exc}")
            raise BookError("文件可能已损坏，或使用了不支持的 CHM 变体。") from exc

    def _collect(self, chm: ChmFile, order: list[str]) -> tuple[list[tuple[str, str]], bool]:
        """按顺序取主题页，受"页数 / 正文体量 / 解压总量"三个预算限制。

        第一页无论多大都会保留（否则预览会是空的），之后的页面一旦超预算就停。
        """
        included: list[tuple[str, str]] = []
        total = 0
        decode_base = chm.decoded_bytes
        for topic in order[: self.max_topics]:
            if included and (
                total >= self.max_html_bytes
                or chm.decoded_bytes - decode_base > self.max_decode_bytes
            ):
                break
            raw = chm.read(topic)
            if raw is None:
                continue
            text = decode_text(raw, chm.language)
            if not looks_like_html(text):
                continue
            included.append((topic, text))
            total += len(text)
        return included, len(included) < len(order)


get_registry("book").register(ChmParser())


__all__ = ["ChmError", "ChmFile", "ChmParser", "LzxDecoder", "LzxError"]
