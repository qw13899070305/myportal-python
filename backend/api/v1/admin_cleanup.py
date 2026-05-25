from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import get_db
from backend.core.auth import RoleChecker
from backend.models.file import FileItem
from backend.core.config import settings
import os

router = APIRouter(prefix="/admin/files", tags=["管理-清理"])

@router.post("/cleanup")
async def cleanup(db: AsyncSession = Depends(get_db), _=Depends(RoleChecker(["admin","super_admin"]))):
    result = await db.execute(select(FileItem).where(FileItem.deleted == True))
    files = result.scalars().all()
    count = 0
    for f in files:
        path = settings.UPLOAD_DIR / f.name
        if path.exists():
            os.remove(path)
            count += 1
    return {"deleted_count": count}
