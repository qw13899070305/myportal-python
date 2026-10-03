"""电子书阅读数据接口（可拆卸扩展）。

``GET /files/{id}/book`` 把 epub / azw3 / mobi / chm 解析成**纯数据 JSON**：

.. code-block:: json

    {
      "file_id": 3, "name": "alice.epub", "size": 136756,
      "format": "epub", "title": "Alice's Adventures in Wonderland",
      "author": "Lewis Carroll", "language": "en",
      "chapter_count": 13, "truncated": false, "note": "",
      "chapters": [
        {"index": 0, "title": "封面", "anchor": "ch0",
         "html": "<div>...</div>", "text": "..."}
      ]
    }

这是给**客户端**用的统一接口：手机 APP、未来的新界面都吃这份 JSON，
自己决定怎么画；网页预览走 ``GET /files/{id}/preview``（HTML）。
两条路共用 :mod:`backend.services.books` 这一套解析器，谁也不依赖谁。

查询参数：

- ``chapter=N``  只返回第 N 节（从 0 开始），大书可以懒加载
- ``html=0``     不要 ``html`` 字段（只要纯文本）
- ``text=0``     不要 ``text`` 字段（只要 HTML）

本文件是可拆卸的：删掉它，网页预览与下载照常工作，只是少了一个给 APP 用的数据接口。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from backend.api.v1.file_common import get_accessible_file, storage_path
from backend.core.database import get_db
from backend.core.security import get_current_user_flexible
from backend.models.user import User
from backend.services.books import BookError, parse_book, supported_extensions

router = APIRouter()


def _supported_text() -> str:
    exts = "、".join(sorted(supported_extensions())) or "（未安装任何解析器）"
    return f"该格式不支持在线阅读，目前支持：{exts}"


@router.get("/{file_id}/book")
async def read_book(
    request: Request,
    file_id: int,
    chapter: int | None = Query(default=None, ge=0, description="只取第 N 节（从 0 开始）"),
    with_html: bool = Query(default=True, alias="html"),
    with_text: bool = Query(default=True, alias="text"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """把书解析成 JSON（解析在解析器里，本接口只负责取文件、鉴权、拼响应）。"""
    item = await get_accessible_file(db, file_id, current_user)
    path = storage_path(item)
    ext = Path(item.stored_name).suffix.lower()

    try:
        # 解析是纯 CPU 活（CHM 还要解 LZX），放线程池别卡住事件循环
        book = await run_in_threadpool(parse_book, path, ext)
    except BookError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from None

    if book is None:
        raise HTTPException(status_code=400, detail=_supported_text())

    picked = book.chapters
    if chapter is not None:
        picked = tuple(node for node in book.chapters if node.index == chapter)
        if not picked:
            raise HTTPException(status_code=404, detail=f"没有第 {chapter} 节")

    payload = book.to_json(
        include_html=with_html,
        include_text=with_text,
        chapters=picked,
    )
    # 客户端拼详情页/下载按钮要用到的文件元信息（不重复 Book 里的字段）
    payload.update(
        {
            "file_id": item.id,
            "name": item.name,
            "size": item.size,
            "content_type": item.content_type,
            "download_url": f"/api/v1/files/{item.id}/download",
        }
    )
    return payload


__all__ = ["router"]
