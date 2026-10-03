"""回收站接口：查看、恢复、彻底删除。

删除文件时（``DELETE /api/v1/files/{id}``）会写一条 :class:`TrashItem`，
这里基于它做恢复与清理；磁盘文件用 ``stored_name`` 定位，
不会因为用户改了展示名而找不到文件。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.security import get_current_user, is_admin
from backend.models.file import FileItem, TrashItem
from backend.models.user import User
from backend.schemas.common import Message
from backend.schemas.file import TrashListOut
from backend.services.audit import safe_log_action

router = APIRouter()


def _purge_from_disk(item: FileItem) -> None:
    """删除磁盘文件；文件已不存在时静默跳过。"""
    base = settings.UPLOAD_DIR.resolve()
    path = (base / item.stored_name).resolve()
    if path.is_relative_to(base):
        path.unlink(missing_ok=True)


async def _get_trash_entry(db: AsyncSession, item_id: int) -> TrashItem:
    entry = await db.get(TrashItem, item_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="回收站中没有该记录")
    return entry


@router.get("/", response_model=TrashListOut)
async def list_trash(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=settings.PAGE_SIZE_MAX),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """回收站列表。普通用户只看自己删除的，管理员看全部。"""
    stmt = select(TrashItem).join(FileItem, FileItem.id == TrashItem.file_id)
    if not is_admin(current_user):
        stmt = stmt.where(FileItem.uploader_id == current_user.id)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    result = await db.execute(
        stmt.order_by(TrashItem.deleted_time.desc(), TrashItem.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return TrashListOut(total=total, items=result.scalars().all())


@router.post("/restore/{item_id}", response_model=Message)
async def restore(
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从回收站恢复文件。"""
    entry = await _get_trash_entry(db, item_id)
    file_item = await db.get(FileItem, entry.file_id)
    if file_item is None:
        # 文件记录已不存在，回收站条目也应清理掉
        await db.delete(entry)
        await db.commit()
        raise HTTPException(status_code=404, detail="原文件记录已不存在")

    if file_item.uploader_id != current_user.id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="无权操作该文件")

    file_item.deleted = False
    db.add(file_item)
    await db.delete(entry)
    await db.commit()

    await safe_log_action(
        db,
        action="file_restore",
        user_id=current_user.id,
        detail=entry.name,
        request=request,
    )
    logger.info(f"用户 {current_user.username} 从回收站恢复文件 {entry.name}")
    return Message(message="文件已恢复")


@router.delete("/permanent/{item_id}", response_model=Message)
async def permanent_delete(
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """彻底删除单个文件（不可恢复）。"""
    entry = await _get_trash_entry(db, item_id)
    file_item = await db.get(FileItem, entry.file_id)

    if file_item is not None:
        if file_item.uploader_id != current_user.id and not is_admin(current_user):
            raise HTTPException(status_code=403, detail="无权操作该文件")
        _purge_from_disk(file_item)
        await db.delete(file_item)

    await db.delete(entry)
    await db.commit()

    await safe_log_action(
        db,
        action="file_purge",
        user_id=current_user.id,
        detail=entry.name,
        request=request,
    )
    logger.info(f"用户 {current_user.username} 彻底删除文件 {entry.name}")
    return Message(message="文件已永久删除")


@router.delete("/", response_model=Message)
async def empty_trash(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清空回收站。普通用户清空自己删除的，管理员清空全部。"""
    stmt = select(TrashItem).join(FileItem, FileItem.id == TrashItem.file_id)
    if not is_admin(current_user):
        stmt = stmt.where(FileItem.uploader_id == current_user.id)

    result = await db.execute(stmt)
    entries = result.scalars().all()

    removed = 0
    for entry in entries:
        file_item = await db.get(FileItem, entry.file_id)
        if file_item is not None:
            _purge_from_disk(file_item)
            await db.delete(file_item)
        await db.delete(entry)
        removed += 1

    await db.commit()
    await safe_log_action(
        db,
        action="trash_empty",
        user_id=current_user.id,
        detail=f"清空 {removed} 个文件",
        request=request,
    )
    return Message(message=f"已清空 {removed} 个文件")
