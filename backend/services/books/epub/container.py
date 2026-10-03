"""EPUB 的容器层：zip、``META-INF/container.xml``、OPF。

只回答两个问题：**这本书里有哪些文件**、**章节按什么顺序读**。
正文怎么清洗、图片怎么内联，是 :mod:`.chapters` / :mod:`.assets` 的事。

- :class:`EpubContainer`：zip 句柄 + 条目名索引（大小写不敏感、URL 解码兜底）
- :func:`book_path`：把书内相对路径规范化成 zip 路径
- :func:`load_package`：DRM 检查 → container.xml → OPF → :class:`Package`
"""

from __future__ import annotations

import posixpath
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from backend.services.books.model import BookError

from .xmlutil import (
    element_text,
    find_all,
    find_first,
    localname,
    parse_xml,
    strip_namespaces,
)

#: 加密标记：见到它就认为整本书带 DRM（字体混淆的少数情况也一并挡掉）
ENCRYPTION_PATH = "META-INF/encryption.xml"
#: 容器清单
CONTAINER_PATH = "META-INF/container.xml"

#: 正文类扩展名（spine 里偶尔混进图片 / 字体 / 封面资源）
CHAPTER_EXTENSIONS = frozenset({".xhtml", ".html", ".htm", ".xml"})
#: 正文类 media-type（spine 为空时按 manifest 顺序兜底要用）
CHAPTER_MEDIA_TYPES = frozenset({"application/xhtml+xml", "text/html"})

_BROKEN = "无法解析这本 EPUB：{}"


@dataclass(frozen=True)
class Package:
    """OPF 的解析结果（纯数据，不含正文）。"""

    #: OPF 在 zip 里的真实条目名
    opf_path: str
    title: str = ""
    author: str = ""
    language: str = ""
    #: 按 spine 顺序排好的正文条目名（zip 内的真实路径）
    chapters: tuple[str, ...] = ()
    #: spine 里声明了、但 zip 里找不到的章节数（解析器据此写 Book.note）
    missing: int = 0

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)


class EpubContainer:
    """一本 EPUB 的 zip 句柄与条目索引（用完 ``close()``，或用 ``with``）。"""

    def __init__(self, path: Path) -> None:
        try:
            self._zip = zipfile.ZipFile(path)
        except (zipfile.BadZipFile, OSError) as exc:
            raise BookError(_BROKEN.format("它不是有效的 zip 容器，文件可能已损坏。")) from exc
        names = self._zip.namelist()
        #: 全部条目名（调试 / 兜底查找用）
        self.names: tuple[str, ...] = tuple(names)
        self._exact = {name: name for name in names}
        self._lower: dict[str, str] = {}
        self._basename: dict[str, list[str]] = {}
        for name in names:
            self._lower.setdefault(name.lower(), name)
            self._basename.setdefault(posixpath.basename(name).lower(), []).append(name)

    def __enter__(self) -> EpubContainer:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        self.close()
        return False

    def close(self) -> None:
        self._zip.close()

    # ---------------- 查找 / 读取 ----------------

    def resolve(self, name: str) -> str | None:
        """书内相对路径 → 真实条目名（大小写不敏感，兼容 ``%20`` 之类的转义）。"""
        if not name:
            return None
        cleaned = posixpath.normpath(unquote(name).replace("\\", "/")).lstrip("/")
        if cleaned in (".", "..") or cleaned.startswith("../"):
            return None
        return self._exact.get(cleaned) or self._lower.get(cleaned.lower())

    def resolve_by_basename(self, name: str) -> str | None:
        """只按文件名找（真实电子书里图片路径写错目录是常事）。"""
        base = posixpath.basename(unquote(name).split("#", 1)[0].split("?", 1)[0])
        found = self._basename.get(base.replace("\\", "/").lower())
        return found[0] if found else None

    def read(self, name: str) -> bytes | None:
        """读一个条目的字节；不存在 / 读不了（含被加密）都返回 ``None``。"""
        try:
            return self._zip.read(name)
        except (KeyError, OSError, RuntimeError, zipfile.BadZipFile):
            return None


def book_path(base_file: str, href: str) -> str:
    """把 ``href`` 相对 ``base_file`` 所在目录规范化成 zip 内路径。

    丢掉 ``#fragment`` / ``?query``，还原 URL 转义，并挡住 ``../`` 跳出书根。
    """
    raw = href.split("#", 1)[0].split("?", 1)[0]
    raw = unquote(raw).replace("\\", "/").strip()
    if not raw:
        return ""
    base_dir = posixpath.dirname(base_file)
    joined = posixpath.normpath(posixpath.join(base_dir, raw) if base_dir else raw)
    if joined in (".", "..") or joined.startswith("../"):
        return ""
    return joined.lstrip("/")


def is_chapter(name: str) -> bool:
    """是不是正文条目（spine 里偶尔混进图片 / 字体 / 封面资源）。"""
    return posixpath.splitext(name)[1].lower() in CHAPTER_EXTENSIONS


def load_package(container: EpubContainer) -> Package:
    """读出书的结构；打不开就抛 :class:`BookError`（DRM 带 ``drm=True``）。"""
    if container.resolve(ENCRYPTION_PATH) is not None:
        raise BookError("这本书有 DRM 加密，无法在线预览，请用支持 DRM 的阅读器打开。", drm=True)

    opf_name = _find_opf(container)
    if opf_name is None:
        raise BookError(_BROKEN.format("缺少 META-INF/container.xml 或其中的 OPF 路径。"))
    opf = parse_xml(container.read(opf_name))
    if opf is None:
        raise BookError(_BROKEN.format("OPF 清单读不出来，文件可能已损坏。"))

    strip_namespaces(opf)
    metadata = find_first(opf, "metadata")
    if metadata is None:
        metadata = opf

    manifest: dict[str, tuple[str, str]] = {}
    for item in find_all(opf, "item"):
        item_id = item.get("id")
        if item_id:
            manifest[item_id] = (
                item.get("href") or "",
                (item.get("media-type") or "").strip().lower(),
            )

    chapters: list[str] = []
    missing = 0
    for itemref in find_all(opf, "itemref"):
        href, media_type = manifest.get(itemref.get("idref") or "", ("", ""))
        if not href or (media_type and media_type not in CHAPTER_MEDIA_TYPES):
            continue
        resolved = container.resolve(book_path(opf_name, href))
        if resolved is None:
            missing += 1  # 声明了却不在包里，交给解析器记一笔
        elif is_chapter(resolved):
            chapters.append(resolved)
    if not chapters:
        # spine 为空或全是坏路径时退一步：按 manifest 里正文的声明顺序读
        for href, media_type in manifest.values():
            if media_type not in CHAPTER_MEDIA_TYPES:
                continue
            resolved = container.resolve(book_path(opf_name, href))
            if resolved and is_chapter(resolved):
                chapters.append(resolved)

    return Package(
        opf_path=opf_name,
        title=element_text(find_first(metadata, "title")),
        author=element_text(find_first(metadata, "creator")),
        language=element_text(find_first(metadata, "language")),
        chapters=tuple(chapters),
        missing=missing,
    )


def _find_opf(container: EpubContainer) -> str | None:
    """``META-INF/container.xml`` → OPF 条目名。"""
    container_name = container.resolve(CONTAINER_PATH)
    if container_name is None:
        return None
    root = parse_xml(container.read(container_name))
    if root is None:
        return None
    for elem in root.iter():
        if localname(elem.tag) != "rootfile":
            continue
        resolved = container.resolve(elem.get("full-path") or "")
        if resolved:
            return resolved
    # container.xml 里没写 rootfile 时，兜底找唯一的 .opf
    opfs = [name for name in container.names if name.lower().endswith(".opf")]
    return opfs[0] if len(opfs) == 1 else None


__all__ = [
    "CHAPTER_EXTENSIONS",
    "CHAPTER_MEDIA_TYPES",
    "CONTAINER_PATH",
    "ENCRYPTION_PATH",
    "EpubContainer",
    "Package",
    "book_path",
    "is_chapter",
    "load_package",
]
