"""文件下载接口（可拆卸扩展）。

- ``GET /files/{id}/download``  下载原文件
- ``GET /files/download/{id}``  同上（兼容旧前端路径）

两者都支持 ``?token=`` 认证，因为浏览器 ``<a download>`` 无法自定义请求头。

同时注册 ``HEAD``：与 Starlette 的 ``Route`` 不同，FastAPI 的 ``APIRoute``
**不会**自动给 GET 路由加 HEAD，手机上的下载管理器（先发 HEAD 探大小/文件名）
会因此落到前端静态回退里拿到 index.html。``FileResponse`` 自己会处理
HEAD（只发头不发体），所以这里只要把方法注册上就行。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.file_common import get_accessible_file, storage_path
from backend.core.database import get_db
from backend.core.security import get_current_user_flexible
from backend.models.user import User

router = APIRouter()


@router.api_route("/{file_id}/download", methods=["GET", "HEAD"])
async def download_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """下载原文件（支持 ``?token=``）。"""
    item = await get_accessible_file(db, file_id, current_user)
    return FileResponse(
        storage_path(item),
        filename=item.name,
        media_type=item.content_type or "application/octet-stream",
    )


@router.api_route("/download/{file_id}", methods=["GET", "HEAD"])
async def download_file_legacy(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """兼容旧前端 ``GET /files/download/{id}``。"""
    return await download_file(file_id, db=db, current_user=current_user)
