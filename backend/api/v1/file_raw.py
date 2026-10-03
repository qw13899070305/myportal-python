"""原始字节流接口（可拆卸扩展）。

``GET /files/{id}/raw`` 把磁盘上的字节原样吐出来，**inline** 交给客户端：

- 支持 ``Range``（``<video>`` 拖进度条、断点续传都靠它；``FileResponse`` 自带）
- 支持 ``?token=``（``<video>`` / ``<audio>`` / ``<img>`` 没法自定义请求头）
- 只放行"内联安全"的类型，其余一律 415 —— 请走 ``/download``
- **不放行 SVG**（能带脚本）和 HTML（同源内联等于给自己开 XSS 后门）
- 附 ``X-Content-Type-Options: nosniff``

定位：后端只负责**给字节**，播放器长什么样是客户端的事。
网页拿它做 ``<video>`` / ``<audio>`` / ``<img>`` 的数据源，
手机 APP 也可以直接拿它当播放源。删掉本文件不影响下载与预览。
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.file_common import get_accessible_file, storage_path
from backend.core.database import get_db
from backend.core.security import get_current_user_flexible
from backend.models.user import User

router = APIRouter()

#: 可以内联展示的 MIME（不含 image/svg+xml、text/html）
INLINE_MEDIA_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "image/bmp",
        "audio/mpeg",
        "audio/mp4",
        "audio/wav",
        "audio/x-wav",
        "audio/aac",
        "audio/ogg",
        "audio/flac",
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "video/3gpp",
        "video/x-m4v",
        "application/pdf",
    }
)

#: 上传时浏览器常给 ``application/octet-stream``，按扩展名再判一次
INLINE_MEDIA_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".bmp",
        ".mp3",
        ".m4a",
        ".wav",
        ".aac",
        ".ogg",
        ".flac",
        ".mp4",
        ".mov",
        ".3gp",
        ".m4v",
        ".webm",
        ".pdf",
    }
)


@router.api_route("/{file_id}/raw", methods=["GET", "HEAD"])
async def raw_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """原样返回字节（inline），供播放器 / 图片控件直接引用。"""
    item = await get_accessible_file(db, file_id, current_user)
    path = storage_path(item)
    ext = Path(item.stored_name).suffix.lower()
    media_type = (
        item.content_type
        or mimetypes.guess_type(item.name)[0]
        or "application/octet-stream"
    ).split(";")[0].strip().lower()

    if media_type not in INLINE_MEDIA_TYPES and ext not in INLINE_MEDIA_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="该类型不支持内联播放，请使用下载接口",
        )

    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
            # 私有文件：允许浏览器缓存，但别让中间代理存
            "Cache-Control": "private, max-age=3600",
        },
    )


__all__ = ["INLINE_MEDIA_EXTENSIONS", "INLINE_MEDIA_TYPES", "router"]
