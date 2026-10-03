"""文件分类规则的守卫测试。

分类表（``core/filetypes.py``）与上传白名单（``api/v1/file_common.py``）是
两份数据，但必须**完全对齐**：白名单里的每个扩展名都要能分到类，分类表里
也不许出现传不上来的扩展名。这里把它钉死，避免两边各自漂移。
"""

import pytest

from backend.api.v1.file_common import ALLOWED_EXTENSIONS
from backend.core.filetypes import (
    CATEGORY_EXTENSIONS,
    CATEGORY_ORDER,
    CATEGORY_OTHER,
    all_categories,
    categorized_extensions,
    category_of,
    extensions_of,
    known_categories,
)


def test_categories_cover_upload_whitelist_exactly():
    """分类与上传白名单必须一一对齐（不多、不少）。"""
    assert categorized_extensions() == set(ALLOWED_EXTENSIONS)
    assert not set(ALLOWED_EXTENSIONS) - categorized_extensions(), "有能上传却分不了类的类型"


def test_category_keys_and_order_are_stable():
    """分类键与顺序是对外契约，客户端按它排标签。"""
    assert all_categories() == CATEGORY_ORDER
    assert CATEGORY_OTHER == CATEGORY_ORDER[-1]
    assert set(known_categories()) == set(CATEGORY_EXTENSIONS)
    assert CATEGORY_OTHER not in CATEGORY_EXTENSIONS  # other 是兜底，没有固定扩展名


def test_no_extension_belongs_to_two_categories():
    seen: dict[str, str] = {}
    for category, extensions in CATEGORY_EXTENSIONS.items():
        for ext in extensions:
            assert ext == ext.lower(), f"{ext} 必须是小写"
            assert ext.startswith("."), f"{ext} 必须带点"
            assert ext not in seen, f"{ext} 同时属于 {seen.get(ext)} 和 {category}"
            seen[ext] = category


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("photo.JPG", "image"),
        ("IMG_0001.heic", "image"),
        ("report.pdf", "document"),
        ("notes.txt", "document"),
        ("book.epub", "ebook"),
        ("book.azw3", "ebook"),
        ("help.chm", "ebook"),
        ("movie.mp4", "video"),
        ("song.m4a", "audio"),
        ("backup.zip", "archive"),
        ("noextension", CATEGORY_OTHER),
        ("evil.exe", CATEGORY_OTHER),
        ("archive.tar.gz", CATEGORY_OTHER),
        ("", CATEGORY_OTHER),
        (None, CATEGORY_OTHER),
    ],
)
def test_category_of(name, expected):
    assert category_of(name) == expected


def test_extensions_of_unknown_category_is_empty():
    assert extensions_of("nope") == frozenset()
    assert extensions_of(CATEGORY_OTHER) == frozenset()
    assert ".jpg" in extensions_of("image")
