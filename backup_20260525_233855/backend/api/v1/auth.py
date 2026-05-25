import os, uuid, bleach
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import get_db
from backend.core.auth import create_access_token, get_current_user, RoleChecker
from backend.core.config import settings
from backend.core.security import check_login_throttle, record_failed_login
from backend.core.utils import sanitize_filename
from backend.models.user import User
from backend.models.chat import Notification
from pydantic import BaseModel, EmailStr, field_validator

router = APIRouter(prefix="/auth", tags=["认证"])

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str
    email: EmailStr

    @field_validator("username")
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError("用户名只能包含字母和数字")
        return v

    @field_validator("password")
    def password_strength(cls, v):
        # ✅ 新增密码强度验证
        if len(v) < 8:
            raise ValueError("密码长度至少8位")
        if not any(c.islower() for c in v):
            raise ValueError("密码需包含小写字母")
        if not any(c.isupper() for c in v):
            raise ValueError("密码需包含大写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码需包含数字")
        return v

    @field_validator("confirm_password")
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError("两次密码不一致")
        return v

@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "用户名已存在")
    user = User(username=req.username, email=req.email)
    user.set_password(req.password)
    db.add(user)
    await db.commit()
    return {"message": "注册成功"}

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    # ✅ 登录限流（内存版，生产环境请用 Redis）
    check_login_throttle(req.username)
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not user.verify_password(req.password):
        record_failed_login(req.username)
        raise HTTPException(401, "用户名或密码错误")
    roles = [role.name for role in user.roles]
    token = create_access_token({"sub": str(user.id), "roles": roles})

    # ✅ 改为 HttpOnly Cookie 方式，同时保留响应体中的 token 以兼容旧版
    response = JSONResponse({"access_token": token, "token_type": "bearer", "roles": roles, "user_id": user.id})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False if settings.DEBUG else True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return response

@router.post("/switch-role")
async def switch_role(role_name: str, user: User = Depends(get_current_user)):
    if not user.has_role(role_name):
        raise HTTPException(403, "你没有该角色")
    # ✅ 修复：新 token 只包含切换后的单一角色
    token = create_access_token({"sub": str(user.id), "roles": [role_name]})
    return {"access_token": token, "token_type": "bearer", "roles": [role_name]}

@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(..., max_size=2*1024*1024),  # ✅ 限制头像大小为2MB
                        user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "仅支持图片格式")
    safe_name = f"avatar_{user.id}_{uuid.uuid4().hex}{os.path.splitext(sanitize_filename(file.filename))[1]}"
    file_path = settings.UPLOAD_DIR / "avatars" / safe_name
    settings.UPLOAD_DIR.mkdir(exist_ok=True)
    (settings.UPLOAD_DIR / "avatars").mkdir(exist_ok=True)
    content = await file.read()
    file_path.write_bytes(content)
    user.avatar = safe_name
    db.add(user)
    await db.commit()
    return {"avatar": safe_name, "url": f"/api/v1/files/avatar/{safe_name}"}

@router.get("/notifications")
async def get_notifications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(20)
    )
    notifs = result.scalars().all()
    return [{"id": n.id, "type": n.type, "content": n.content, "is_read": n.is_read, "time": str(n.created_at)} for n in notifs]
