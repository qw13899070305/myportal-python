"""文件在线预览接口（可拆卸扩展）。

挂载在 ``/api/v1/files`` 下：

- ``GET /files/{id}/preview``        在线预览（图片/PDF 内联，Office 转 HTML）
- ``GET /files/preview/{id}``        同上（兼容旧前端路径）
- ``GET /files/{id}/pdf-info``       PDF 总页数
- ``GET /files/{id}/pdf-page/{n}``   PDF 第 n 页渲染成 JPEG

真正干活的渲染器是 :mod:`backend.extensions.preview` 里的扩展，
本文件只做「取文件 → 找扩展 → 转成响应」。
把本文件删掉，文件的上传/下载/增删改全部照常工作。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from backend.api.v1.file_common import get_accessible_file, storage_path
from backend.core.database import get_db
from backend.core.security import get_current_user, get_current_user_flexible
from backend.extensions.preview import PREVIEW_SECURITY_HEADERS, render_preview
from backend.models.user import User

router = APIRouter()


@router.get("/{file_id}/preview")
async def preview_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """在线预览：图片/PDF 内联展示，其余格式交给预览扩展转 HTML。

    支持 ``?token=`` 认证，因为 iframe 无法自定义请求头。
    """
    item = await get_accessible_file(db, file_id, current_user)
    path = storage_path(item)
    ext = Path(item.stored_name).suffix.lower()

    # 渲染放在线程池里：EPUB / AZW3 / CHM 这些纯 Python 解析器可能要跑几秒，
    # 直接在事件循环里跑会把整个服务卡住
    preview = await run_in_threadpool(render_preview, path, ext)
    if preview is None:
        raise HTTPException(status_code=400, detail=f"{ext or '该'} 格式暂不支持在线预览")

    if preview.kind == "file":
        return FileResponse(
            path,
            media_type=preview.media_type or "application/octet-stream",
            headers={"Content-Disposition": "inline", **PREVIEW_SECURITY_HEADERS},
        )
    return HTMLResponse(preview.html or "", headers=PREVIEW_SECURITY_HEADERS)


@router.get("/preview/{file_id}")
async def preview_file_legacy(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """兼容旧前端 ``GET /files/preview/{id}``。"""
    return await preview_file(file_id, db=db, current_user=current_user)


@router.get("/{file_id}/pdf-info")
async def pdf_info(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """PDF 总页数（依赖 pdf 预览扩展的可选能力）。"""
    item = await get_accessible_file(db, file_id, current_user)
    if Path(item.stored_name).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="该文件不是 PDF")

    from backend.services.preview import get_pdf_page_count

    return {"page_count": get_pdf_page_count(storage_path(item))}


@router.get("/{file_id}/pdf-page/{page_num}")
async def pdf_page_image(
    file_id: int,
    page_num: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """把 PDF 指定页渲染成 JPEG（供前端翻页预览）。"""
    item = await get_accessible_file(db, file_id, current_user)
    if Path(item.stored_name).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="该文件不是 PDF")

    from backend.services.preview import preview_pdf_page

    try:
        image = preview_pdf_page(storage_path(item), page_num)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return Response(content=image, media_type="image/jpeg")
