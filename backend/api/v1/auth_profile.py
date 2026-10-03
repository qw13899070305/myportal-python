"""账号资料接口（可拆卸扩展）。

- ``GET  /auth/me``              当前登录用户信息
- ``POST /auth/change-password`` 修改密码
- ``GET  /auth/check-username``  注册页实时校验用户名是否可用
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.password import verify_password
from backend.core.security import get_current_user
from backend.models.user import User
from backend.schemas.common import Message
from backend.schemas.user import PasswordChange, UserOut
from backend.services.audit import log_action

router = APIRouter()


@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """返回当前登录用户信息。"""
    return current_user


@router.post("/change-password", response_model=Message)
async def change_password(
    request: Request,
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户密码。"""
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="当前密码错误")
    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")

    current_user.set_password(payload.new_password)
    db.add(current_user)
    await log_action(db, action="change_password", user_id=current_user.id, request=request)
    await db.commit()
    logger.info(f"用户修改密码: {current_user.username}")
    return Message(message="密码修改成功")


@router.get("/check-username")
async def check_username(
    username: str = Query(..., min_length=1, max_length=50),
    db: AsyncSession = Depends(get_db),
):
    """注册页可用来实时提示用户名是否已被占用。"""
    exists = await db.scalar(select(User.id).where(User.username == username))
    return {"username": username, "available": exists is None}
