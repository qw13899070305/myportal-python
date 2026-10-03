"""文件的元信息与修改接口（可拆卸扩展）。

- ``GET    /files/{id}``              查看元信息
- ``PATCH  /files/{id}``              重命名
- ``PUT    /files/rename/{id}``       重命名（兼容旧前端）
- ``DELETE /files/{id}``              软删除（移入回收站）

**必须挂载在 ``/files/list``、``/files/recent``、``/files/upload``
这些固定路径之后**，否则 ``/{file_id}`` 会抢先匹配。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.file_common import (
    get_accessible_file,
    validate_extension,
)
from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.core.utils import utcnow
from backend.models.file import TrashItem
from backend.models.user import User
from backend.schemas.common import Message
from backend.schemas.file import FileOut, FileRename
from backend.services.audit import safe_log_action

router = APIRouter()


@router.get("/{file_id}", response_model=FileOut)
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查看文件元信息。"""
    return await get_accessible_file(db, file_id, current_user)


@router.patch("/{file_id}", response_model=FileOut)
async def rename_file(
    file_id: int,
    payload: FileRename,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重命名文件（只改展示名，磁盘文件名不变）。"""
    item = await get_accessible_file(db, file_id, current_user)
    validate_extension(payload.name)  # 不允许改成危险扩展名
    item.name = payload.name
    db.add(item)
    await db.commit()
    return item


@router.put("/rename/{file_id}", response_model=FileOut)
async def rename_file_legacy(
    file_id: int,
    new_name: str = Query(..., min_length=1, max_length=255),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重命名（兼容旧前端 ``PUT /files/rename/{id}?new_name=``）。"""
    return await rename_file(file_id, FileRename(name=new_name), db=db, current_user=current_user)


@router.delete("/{file_id}", response_model=Message)
async def delete_file(
    file_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """软删除：移入回收站，可以在回收站里恢复。"""
    item = await get_accessible_file(db, file_id, current_user)
    if item.deleted:
        raise HTTPException(status_code=400, detail="文件已在回收站中")

    item.deleted = True
    db.add(item)
    db.add(
        TrashItem(
            file_id=item.id,
            name=item.name,
            size=item.size,
            deleted_time=utcnow(),
        )
    )
    await db.commit()

    await safe_log_action(
        db,
        action="file_delete",
        user_id=current_user.id,
        detail=item.name,
        request=request,
    )
    return Message(message="已移入回收站")
