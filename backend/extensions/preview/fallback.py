"""兜底预览扩展。

优先级最低、匹配一切，因此**必须最后被匹配到**。
把本文件删掉也不会出错：``find_handler`` 会返回 None，
接口层会给出同样的提示。
"""

from __future__ import annotations

from pathlib import Path

from backend.extensions.preview.base import Preview, PreviewHandler
from backend.extensions.registry import get_registry


class FallbackPreview(PreviewHandler):
    name = "fallback"
    extensions = frozenset()
    # 负数优先级保证排在所有真实格式扩展之后
    priority = -100

    def matches(self, ext: str) -> bool:
        return True

    def render(self, path: Path) -> Preview:
        ext = path.suffix or "该"
        return self.message_page(
            f"{ext} 格式暂不支持在线预览",
            "请下载后用本地软件打开。",
        )


get_registry("preview").register(FallbackPreview())
