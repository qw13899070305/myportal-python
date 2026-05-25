import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.core.config import settings
from backend.models.share import ShareLink
from pydantic import BaseModel

router = APIRouter(prefix="/share", tags=["分享"])

class ShareCreate(BaseModel):
    filename: str
    password: str | None = None
    expire_hours: int = settings.SHARE_LINK_EXPIRE_HOURS

@router.post("/create")
async def create(data: ShareCreate, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    code = secrets.token_urlsafe(8)
    expire_at = datetime.utcnow() + timedelta(hours=data.expire_hours)
    link = ShareLink(file_path=data.filename, code=code, password=data.password, expire_at=expire_at, created_by=user.id)
    db.add(link)
    await db.commit()
    return {"code": code, "expire_at": expire_at, "password": data.password}

@router.get("/access/{code}")
async def access(code: str, password: str | None = None, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ShareLink).where(ShareLink.code == code, ShareLink.is_active == True))
    link = result.scalar_one_or_none()
    if not link: raise HTTPException(404, "分享不存在或已失效")
    if link.expire_at < datetime.utcnow():
        link.is_active = False; await db.commit()
        raise HTTPException(410, "分享已过期")
    if link.password and link.password != password:
        raise HTTPException(403, "密码错误")
    return {"filename": link.file_path, "download_url": f"/api/files/download/{link.file_path}"}
