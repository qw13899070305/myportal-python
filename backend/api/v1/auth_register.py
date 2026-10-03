"""注册接口（可拆卸扩展）。

``POST /auth/register`` —— 注册新用户，默认分配 ``user`` 角色
（不允许自行指定角色，避免提权）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.csrf import verify_csrf
from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.rate_limit import limiter
from backend.models.user import DEFAULT_ROLE, create_user, get_user_by_email, get_user_by_username
from backend.schemas.user import UserCreate, UserOut
from backend.services.audit import safe_log_action

router = APIRouter()


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """注册新用户。"""
    if await get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    if user_data.email and await get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = await create_user(
        db,
        username=user_data.username,
        password=user_data.password,
        email=user_data.email,
        roles=[DEFAULT_ROLE],
    )
    await safe_log_action(
        db, action="register", user_id=user.id, detail=user.username, request=request
    )
    logger.info(f"新用户注册: {user.username}")
    return user
