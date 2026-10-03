"""图片预览扩展。

图片不需要转码，直接交给浏览器内联显示即可；
``media_type`` 由调用方结合原始文件名判断。
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from backend.extensions.preview.base import Preview, PreviewHandler
from backend.extensions.registry import get_registry


class ImagePreview(PreviewHandler):
    name = "image"
    extensions = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})
    priority = 10

    #: 兜底的 MIME 类型（按扩展名猜不出来时使用）
    fallback_media_type = "application/octet-stream"

    def render(self, path: Path) -> Preview:
        media_type = mimetypes.guess_type(path.name)[0] or self.fallback_media_type
        return Preview.inline_file(media_type)


get_registry("preview").register(ImagePreview())
