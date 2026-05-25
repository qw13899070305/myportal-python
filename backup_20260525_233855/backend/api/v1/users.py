from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import get_db
from backend.core.auth import RoleChecker, get_current_user
from backend.models.user import User, Role
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["用户"])

class ApplicationCreate(BaseModel):
    username: str
    password: str
    requested_role: str

@router.post("/apply")
async def apply(data: ApplicationCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(User).where(User.username == data.username))
    if exists.scalar_one_or_none():
        raise HTTPException(400, "用户名已存在")
    user = User(username=data.username)
    user.set_password(data.password)
    result = await db.execute(select(Role).where(Role.name == data.requested_role))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(400, "角色不存在")
    user.roles.append(role)
    db.add(user)
    await db.commit()
    return {"msg": "申请成功，等待管理员激活"}

@router.post("/approve/{user_id}")
async def approve(user_id: int, _=Depends(RoleChecker(["admin","super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")
    user.is_active = True
    await db.commit()
    return {"msg": "已激活"}
