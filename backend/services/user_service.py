"""用户服务层。

统一的 ``create_user`` 签名是 ``(db, username, password, email)``。
这里全部转发到 :mod:`backend.models.user`，避免两处实现漂移
（此前本模块与 models 里的 ``create_user`` 参数顺序不同，
会把邮箱和密码写反）。
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User, get_user_by_id, get_user_by_username
from backend.models.user import create_user as _create_user

logger = logging.getLogger(__name__)

__all__ = [
    "authenticate_user",
    "create_user",
    "get_user_by_id",
    "get_user_by_username",
    "update_user_password",
]


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    email: str | None = None,
    roles: list[str] | None = None,
) -> User:
    """创建用户；用户名已存在时抛 ``ValueError``。"""
    existing = await get_user_by_username(db, username)
    if existing:
        raise ValueError("用户名已存在")
    return await _create_user(db, username=username, password=password, email=email, roles=roles)


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """校验用户名密码，成功返回用户对象，失败返回 None。"""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not user.check_password(password):
        return None
    return user


async def update_user_password(db: AsyncSession, user_id: int, new_password: str) -> bool:
    """修改指定用户密码。"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    user.set_password(new_password)
    db.add(user)
    await db.commit()
    return True
