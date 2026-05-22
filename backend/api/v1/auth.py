import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import get_db
from backend.core.config import settings
from backend.core.security import check_login_throttle, record_failed_login, reset_login_attempts
from backend.core.auth import create_access_token, get_current_user
from backend.models.user import User
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["认证"])

class LoginReq(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(request: Request, data: LoginReq, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    check_login_throttle(ip)
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user or not user.verify_password(data.password):
        record_failed_login(ip)
        raise HTTPException(401, "用户名或密码错误")
    reset_login_attempts(ip)
    roles = [role.name for role in user.roles]
    token = create_access_token({"sub": str(user.id), "roles": roles})
    return {
        "access_token": token,
        "token_type": "bearer",
        "roles": roles,
        "user": {"id": user.id, "username": user.username, "avatar_url": user.avatar_url, "roles": [role.name for role in user.roles]}
    }

@router.post("/switch-role")
async def switch_role(role_name: str, user: User = Depends(get_current_user)):
    if not user.has_role(role_name):
        raise HTTPException(403, "你没有该角色")
    roles = [role.name for role in user.roles]
    token = create_access_token({"sub": str(user.id), "roles": roles})
    return {"access_token": token, "roles": roles}

@router.post("/change-password")
async def change_password(old_password: str, new_password: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user.verify_password(old_password):
        raise HTTPException(403, "当前密码错误")
    user.set_password(new_password)
    await db.commit()
    return {"msg": "密码已修改"}
@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 校验图片类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "只允许上传图片")
    avatar_dir = settings.UPLOAD_DIR / "avatars"
    avatar_dir.mkdir(exist_ok=True)
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"avatar_{user.id}_{int(datetime.utcnow().timestamp())}{ext}"
    file_path = avatar_dir / filename
    content = await file.read()
    file_path.write_bytes(content)
    user.avatar_url = f"/api/v1/files/avatar/{filename}"
    await db.commit()
    return {"avatar_url": user.avatar_url}

@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "roles": [r.name for r in user.roles],
        "created_at": user.created_at
    }
