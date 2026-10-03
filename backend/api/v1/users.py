"""用户接口：注册申请、审批、列表、详情。"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.csrf import verify_csrf
from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.security import (
    RoleChecker,
    get_current_user,
    is_admin,
)
from backend.models.user import (
    BUILTIN_ROLES,
    DEFAULT_ROLE,
    User,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
)
from backend.schemas.user import UserApply, UserListOut, UserOut
from backend.services.audit import safe_log_action

router = APIRouter()

#: 客户端可以申请的角色（管理类角色一律不允许自行申请）
APPLICABLE_ROLES = {"user", "reader"}

admin_only = RoleChecker(["admin", "super_admin"])


@router.post(
    "/apply",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def apply_account(
    request: Request,
    data: UserApply,
    db: AsyncSession = Depends(get_db),
):
    """注册申请（兼容旧前端的 ``POST /users/apply``）。

    只会分配普通角色；``requested_role`` 里填管理类角色会被忽略，
    避免客户端自行提权。
    """
    if await get_user_by_username(db, data.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    if data.email and await get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    role = data.requested_role if data.requested_role in APPLICABLE_ROLES else DEFAULT_ROLE
    if role not in BUILTIN_ROLES:  # pragma: no cover - 兜底
        role = DEFAULT_ROLE

    user = await create_user(
        db,
        username=data.username,
        password=data.password,
        email=data.email,
        roles=[role],
    )
    await safe_log_action(
        db,
        action="register",
        user_id=user.id,
        detail=f"{user.username} (via /users/apply, role={role})",
        request=request,
    )
    logger.info(f"新用户注册（apply）: {user.username} 角色={role}")
    return user


@router.post("/approve/{user_id}", response_model=UserOut)
async def approve_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(admin_only),
):
    """启用某个被禁用的账号（管理员）。"""
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_active = True
    db.add(user)
    await safe_log_action(
        db,
        action="user_approve",
        user_id=current_admin.id,
        detail=f"启用用户 {user.username}",
        request=request,
    )
    await db.commit()
    return user


@router.get("/", response_model=UserListOut)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(settings.PAGE_SIZE_DEFAULT, ge=1, le=settings.PAGE_SIZE_MAX),
    search: str = Query("", max_length=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
):
    """管理员：分页列出全部用户。"""
    conditions = []
    if search.strip():
        conditions.append(User.username.ilike(f"%{search.strip()}%"))

    total = await db.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
    result = await db.execute(
        select(User).where(*conditions).order_by(User.id).offset((page - 1) * size).limit(size)
    )
    return UserListOut(total=total, items=result.scalars().all())


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查看用户资料：仅本人或管理员可见。"""
    if user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="无权查看该用户")

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("/{user_id}/toggle-active", response_model=UserOut)
async def toggle_user_active(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(admin_only),
):
    """启用 / 禁用用户（管理员，兼容前端的 ``toggle-active`` 路径）。"""
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能禁用当前登录的账号")

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_active = not user.is_active
    db.add(user)
    await safe_log_action(
        db,
        action="user_toggle_active",
        user_id=current_admin.id,
        detail=f"{'启用' if user.is_active else '禁用'}用户 {user.username}",
        request=request,
    )
    await db.commit()
    return user
