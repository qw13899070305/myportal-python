from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from backend.core.database import get_db
from backend.core.auth import RoleChecker, get_current_user
from backend.models.article import Article
from backend.models.file import FileItem
from backend.models.user import User, Role
from backend.models.config import SiteConfig
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["管理后台"], dependencies=[Depends(RoleChecker(["admin","super_admin"]))])

@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    ac = await db.scalar(select(func.count(Article.id)))
    fc = await db.scalar(select(func.count(FileItem.id).where(FileItem.deleted == False)))
    uc = await db.scalar(select(func.count(User.id)))
    return {"articles": ac, "files": fc, "users": uc}

class ConfigUpdate(BaseModel):
    site_name: str = "myportal-python"
    announcement: str = "欢迎使用"

@router.get("/config")
async def get_config(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SiteConfig))
    configs = result.scalars().all()
    config_dict = {c.key: c.value for c in configs}
    return {
        "site_name": config_dict.get("site_name", "myportal-python"),
        "announcement": config_dict.get("announcement", "欢迎使用")
    }

@router.post("/config")
async def update_config(data: ConfigUpdate, db: AsyncSession = Depends(get_db)):
    for key, value in {"site_name": data.site_name, "announcement": data.announcement}.items():
        result = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
        config = result.scalar_one_or_none()
        if config:
            config.value = value
        else:
            db.add(SiteConfig(key=key, value=value))
    await db.commit()
    return {"msg": "配置已更新"}

@router.get("/users")
async def list_users(page: int=1, limit: int=20, db: AsyncSession = Depends(get_db)):
    q = select(User).order_by(User.created_at.desc())
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    users = (await db.execute(q.offset((page-1)*limit).limit(limit))).scalars().all()
    return {"total": total, "items": [{"id":u.id,"username":u.username,"is_active":u.is_active,"roles":[r.name for r in u.roles],"created_at":u.created_at} for u in users]}

@router.post("/users/{user_id}/role")
async def assign_role(user_id: int, role_name: str, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user: raise HTTPException(404)
    role_result = await db.execute(select(Role).where(Role.name == role_name))
    role = role_result.scalar_one_or_none()
    if not role: raise HTTPException(400, "角色不存在")
    if role not in user.roles:
        user.roles.append(role)
        await db.commit()
    return {"msg": f"已授予 {role_name} 角色"}

@router.post("/users/{user_id}/toggle-active")
async def toggle_active(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user: raise HTTPException(404)
    user.is_active = not user.is_active
    await db.commit()
    return {"msg": "已切换状态", "is_active": user.is_active}
