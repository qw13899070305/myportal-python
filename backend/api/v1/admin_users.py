"""后台 · 用户管理（可拆卸扩展）。

挂载在 ``/api/v1/admin`` 下：

- ``GET  /admin/users``                      用户列表
- ``POST /admin/users/{id}/toggle-active``   启用 / 禁用

把本文件删掉，其余后台功能不受影响
（普通用户侧的 ``/users/approve/{id}`` 仍可启用账号）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.security import RoleChecker
from backend.models.user import User
from backend.schemas.user import UserListOut, UserOut
from backend.services.audit import safe_log_action

router = APIRouter()

admin_only = RoleChecker(["admin", "super_admin"])


@router.get("/users", response_model=UserListOut)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(settings.PAGE_SIZE_DEFAULT, ge=1, le=settings.PAGE_SIZE_MAX),
    search: str = Query("", max_length=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
):
    """用户列表（支持按用户名模糊搜索）。"""
    conditions = []
    if search.strip():
        conditions.append(User.username.ilike(f"%{search.strip()}%"))

    total = await db.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
    result = await db.execute(
        select(User).where(*conditions).order_by(User.id).offset((page - 1) * size).limit(size)
    )
    return UserListOut(total=total, items=result.scalars().all())


@router.post("/users/{user_id}/toggle-active", response_model=UserOut)
async def toggle_user_active(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(admin_only),
):
    """启用 / 禁用用户（不能禁用自己）。"""
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能禁用当前登录的账号")

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_active = not user.is_active
    db.add(user)
    await db.commit()

    await safe_log_action(
        db,
        action="user_toggle_active",
        user_id=current_admin.id,
        detail=f"{'启用' if user.is_active else '禁用'} {user.username}",
        request=request,
    )
    logger.info(
        f"管理员 {current_admin.username} 将用户 {user.username} "
        f"{'启用' if user.is_active else '禁用'}"
    )
    return user
