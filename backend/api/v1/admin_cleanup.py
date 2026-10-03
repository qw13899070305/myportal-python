"""后台文件清理：彻底删除回收站中的文件，释放磁盘空间。"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.security import RoleChecker
from backend.models.file import FileItem, TrashItem
from backend.models.user import User
from backend.services.audit import safe_log_action

router = APIRouter()

admin_only = RoleChecker(["admin", "super_admin"])


@router.post("/cleanup")
async def cleanup(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(admin_only),
):
    """清理回收站：删除磁盘文件 + 数据库记录。

    注意用 ``stored_name`` 定位磁盘文件——``name`` 是用户可改的展示名，
    用它拼路径既找不到文件也有路径穿越风险。
    """
    result = await db.execute(select(FileItem).where(FileItem.deleted.is_(True)))
    items = result.scalars().all()

    base = settings.UPLOAD_DIR.resolve()
    removed = 0
    for item in items:
        path = (base / item.stored_name).resolve()
        if path.is_relative_to(base) and path.is_file():
            path.unlink(missing_ok=True)
            removed += 1
        # 同时清掉对应的回收站条目
        entries = await db.execute(select(TrashItem).where(TrashItem.file_id == item.id))
        for entry in entries.scalars().all():
            await db.delete(entry)
        await db.delete(item)

    await db.commit()
    await safe_log_action(
        db,
        action="files_cleanup",
        user_id=current_admin.id,
        detail=f"清理 {removed} 个文件",
        request=request,
    )
    logger.warning(f"管理员 {current_admin.username} 清理了 {removed} 个回收站文件")
    return {"deleted_count": removed, "message": f"已清理 {removed} 个文件"}
