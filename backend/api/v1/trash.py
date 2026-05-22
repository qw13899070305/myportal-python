import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.core.database import get_db
from backend.core.auth import get_current_user, RoleChecker
from backend.core.config import settings
from backend.models.file import FileItem, TrashItem

router = APIRouter(prefix="/trash", tags=["回收站"])

@router.get("/")
async def list_trash(page: int=1, limit: int=20, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(TrashItem).order_by(TrashItem.deleted_time.desc())
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    items = await db.execute(q.offset((page-1)*limit).limit(limit))
    trash = items.scalars().all()
    return {"total": total, "items": [{"id":t.id,"name":t.name,"size":t.size,"deleted_time":t.deleted_time} for t in trash]}

@router.post("/restore/{item_id}")
async def restore(item_id: int, _=Depends(RoleChecker(["admin","super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrashItem).where(TrashItem.id == item_id))
    t = result.scalar_one_or_none()
    if not t: raise HTTPException(404)
    file_result = await db.execute(select(FileItem).where(FileItem.id == t.file_id))
    f = file_result.scalar_one_or_none()
    if f: f.deleted = False
    await db.delete(t)
    await db.commit()
    return {"msg":"已恢复"}

@router.delete("/permanent/{item_id}")
async def permanent_delete(item_id: int, _=Depends(RoleChecker(["admin","super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrashItem).where(TrashItem.id == item_id))
    t = result.scalar_one_or_none()
    if t:
        fp = os.path.join(settings.UPLOAD_DIR, t.name)
        if os.path.exists(fp): os.remove(fp)
        await db.delete(t)
        await db.commit()
    return {"msg":"已永久删除"}
