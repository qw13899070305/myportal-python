"""文件分类：**唯一的一份**"什么扩展名算哪一类"的规则。

这一层是纯知识，不认识数据库、不认识 HTTP、也不产生界面文案：

- 后端各接口（列表、上传、回收站、搜索）都用 :func:`category_of` 派生分类
- 网页与 APP 拿到的都是**机器键**（``image`` / ``document`` …），
  中文、英文、图标由客户端自己翻译 —— 后端不返回"图片"这种展示文案
- 分类是**按文件名实时派生**的，不存数据库：改文件名就跟着变，
  也不需要在白名单调整时回填历史数据

分类只覆盖"能上传的类型"；不在表里的（无扩展名、``.exe``、历史遗留）
一律落到 ``other``。上传白名单与分类的覆盖关系由
``backend/tests/test_file_types.py`` 钉住，两边不会各自漂移。
"""

from __future__ import annotations

import os

#: 分类键的稳定顺序（客户端按这个顺序排标签）
CATEGORY_ORDER: tuple[str, ...] = (
    "image",
    "document",
    "ebook",
    "video",
    "audio",
    "archive",
    "other",
)

#: 兜底分类：不在任何已知类别里
CATEGORY_OTHER = "other"

#: 分类 -> 扩展名集合。**改这里等于改对外契约**，同时确认上传白名单能覆盖。
CATEGORY_EXTENSIONS: dict[str, frozenset[str]] = {
    # 图片（含手机相册的 heic/heif）
    "image": frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".heic", ".heif"}),
    # 文档：文本、PDF、Office（含只能下载的旧版 Office）
    "document": frozenset(
        {
            ".txt", ".md", ".csv", ".json", ".log",
            ".pdf",
            ".docx", ".xlsx", ".pptx",
            ".doc", ".xls", ".ppt",
        }
    ),
    # 电子书 / 帮助文件：能在线阅读的都在这里
    "ebook": frozenset({".epub", ".azw3", ".mobi", ".chm"}),
    "video": frozenset({".mp4", ".mov", ".3gp", ".m4v"}),
    "audio": frozenset({".mp3", ".m4a", ".wav"}),
    "archive": frozenset({".zip"}),
}

#: 扩展名 -> 分类（反查表，模块加载时建好）
_EXTENSION_CATEGORY: dict[str, str] = {
    ext: category
    for category, extensions in CATEGORY_EXTENSIONS.items()
    for ext in extensions
}


def category_of(name: str | None) -> str:
    """按文件名给出分类键（不认识的返回 ``other``）。"""
    ext = os.path.splitext(str(name or ""))[1].lower()
    return _EXTENSION_CATEGORY.get(ext, CATEGORY_OTHER)


def extensions_of(category: str) -> frozenset[str]:
    """某一类包含的扩展名；``other`` 没有固定扩展名，返回空集合。"""
    return CATEGORY_EXTENSIONS.get(category, frozenset())


def known_categories() -> tuple[str, ...]:
    """所有固定分类（不含 ``other``）。"""
    return tuple(key for key in CATEGORY_ORDER if key in CATEGORY_EXTENSIONS)


def all_categories() -> tuple[str, ...]:
    """对外暴露的全部分类键（含 ``other``）。"""
    return CATEGORY_ORDER


def categorized_extensions() -> frozenset[str]:
    """所有分类覆盖到的扩展名（应与上传白名单一致）。"""
    return frozenset(_EXTENSION_CATEGORY)


__all__ = [
    "CATEGORY_EXTENSIONS",
    "CATEGORY_ORDER",
    "CATEGORY_OTHER",
    "all_categories",
    "categorized_extensions",
    "category_of",
    "extensions_of",
    "known_categories",
]
