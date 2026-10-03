"""当前用户解析（依赖注入零件）。

把「怎么从请求里拿到用户」集中在这里：

- :func:`load_user_from_token` —— 校验令牌 + 黑名单 + 启用状态 + 加载角色
- :func:`get_current_user` —— 标准 ``Authorization: Bearer``
- :func:`get_current_user_flexible` —— 额外支持 ``?token=``（iframe / 下载链接用）
- :func:`get_current_user_optional` —— 允许匿名，失败返回 None
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.blacklist import is_token_blacklisted
from backend.core.database import get_db
from backend.core.tokens import CREDENTIALS_HEADERS, decode_token, subject_of
from backend.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


async def load_user_from_token(token: str, db: AsyncSession) -> User:
    """根据访问令牌加载用户（含角色、黑名单、启用状态校验）。"""
    payload = decode_token(token, expected_type="access")
    user_id = subject_of(payload)

    if await is_token_blacklisted(payload.get("jti", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已失效，请重新登录",
            headers=CREDENTIALS_HEADERS,
        )

    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers=CREDENTIALS_HEADERS,
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """解析 ``Authorization: Bearer`` 令牌并加载用户。"""
    return await load_user_from_token(token, db)


async def get_current_user_flexible(
    request: Request,
    token: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """同时接受请求头与 ``?token=`` 查询参数的当前用户依赖。

    浏览器在 ``<iframe>`` / ``<a download>`` 中无法自定义请求头，
    文件下载与预览接口因此必须支持查询参数传递令牌。
    """
    raw = token
    if not raw:
        header = request.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            raw = header[7:].strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers=CREDENTIALS_HEADERS,
        )
    return await load_user_from_token(raw, db)


async def get_current_user_optional(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme_optional),
) -> Optional[User]:
    """允许匿名的当前用户：无令牌或令牌无效时返回 None。"""
    if not token:
        return None
    try:
        return await load_user_from_token(token, db)
    except HTTPException:
        return None


__all__ = [
    "get_current_user",
    "get_current_user_flexible",
    "get_current_user_optional",
    "load_user_from_token",
    "oauth2_scheme",
    "oauth2_scheme_optional",
]
