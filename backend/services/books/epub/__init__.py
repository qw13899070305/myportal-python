"""EPUB（.epub）解析器：把一本 EPUB 变成 :class:`Book`（纯数据）。

一个文件一件事：

=========================  ==========================================
模块                        职责
=========================  ==========================================
``container.py``            zip / ``META-INF/container.xml`` / OPF
``chapters.py``             章节 XHTML → 标题 + 清洗后的正文 + 纯文本
``assets.py``               章节图片 → ``data:`` URI（带整书预算）
``xmlutil.py``              XML / XHTML 的通用小工具
``__init__.py``             :class:`EpubParser`：装配 Book + 上限
=========================  ==========================================

产出的是**数据，不是页面**：这里没有 HTML 外壳、没有 CSS、没有界面文案。
网页预览（``extensions/preview/book_base.py``）和手机 APP（``/book`` JSON）
各取所需。

上限命中只置 ``Book.truncated``，怎么提示由客户端决定；个别章节文件缺失
则记进 ``Book.note``。

删掉本包只会让 .epub 没有解析器，其它格式完全不受影响。
"""

from __future__ import annotations

from pathlib import Path

from backend.extensions.registry import get_registry
from backend.services.books import Book, BookError, BookParser

from .assets import InlineBudget
from .chapters import parse_chapter
from .container import EpubContainer, Package, load_package


class EpubParser(BookParser):
    """``.epub`` → :class:`Book`。"""

    name = "epub"
    extensions = frozenset({".epub"})
    priority = 20

    #: 最多解析的章节数
    max_chapters = 200
    #: 所有章节正文 HTML 加起来的上限
    max_html_bytes = 2 * 1024 * 1024
    #: 整本书图片内联的总预算
    max_inline_bytes = 8 * 1024 * 1024

    def parse(self, path: Path) -> Book:
        with EpubContainer(path) as container:
            package = load_package(container)
            return self._build(container, package, path)

    # ---------------- 装配 ----------------

    def _build(self, container: EpubContainer, package: Package, path: Path) -> Book:
        #: 章节 → 页内锚点（带格式前缀 + 序号，与 mobi-0 / chm-topic-0 保持一致的约定）
        anchors = {name: f"epub-{index}" for index, name in enumerate(package.chapters)}
        budget = InlineBudget(self.max_inline_bytes)

        chapters = []
        used_bytes = 0
        truncated = False
        skipped = package.missing  # spine 声明了、包里没有的章节
        for index, chapter_path in enumerate(package.chapters):
            if index >= self.max_chapters:
                truncated = True
                break
            chapter = parse_chapter(
                container,
                chapter_path,
                index=index,
                anchors=anchors,
                budget=budget,
            )
            if chapter is None:
                skipped += 1  # 条目读不出来（缺失/加密），跳过但记一笔
                continue
            size = len(chapter.html.encode("utf-8"))
            if chapters and used_bytes + size > self.max_html_bytes:
                truncated = True  # 至少保证有内容，只截断后面的章节
                break
            used_bytes += size
            chapters.append(chapter)

        if not chapters:
            raise BookError("无法解析这本 EPUB：没有解析出任何可显示的章节内容。")
        return Book(
            format=self.name,
            title=package.title or path.stem,
            author=package.author,
            language=package.language,
            chapters=tuple(chapters),
            truncated=truncated,
            note=f"有 {skipped} 章内容缺失，已跳过。" if skipped else "",
        )


get_registry("book").register(EpubParser())


__all__ = ["EpubParser"]
