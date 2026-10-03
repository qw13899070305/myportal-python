"""JWT 令牌的签发与校验（纯函数零件）。

特点：**不依赖数据库、不依赖任何模型**，只用到配置和 PyJWT，
因此可以被任何模块安全引用，也可以单独替换成别的令牌方案。

令牌里包含三个关键字段：

- ``exp``  过期时间
- ``jti``  唯一 id —— 令牌黑名单 / 撤回功能的前提，必须存在
- ``type`` access / refresh —— 防止拿刷新令牌直接访问业务接口
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException, status
from jwt import PyJWTError

from backend.core.config import settings

#: 401 响应统一带上这个头
CREDENTIALS_HEADERS = {"WWW-Authenticate": "Bearer"}

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def encode(data: dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    """底层签发函数：补上 exp / iat / jti / type 后编码。"""
    to_encode = data.copy()
    now = datetime.now(UTC)
    to_encode.update(
        {
            "exp": now + expires_delta,
            "iat": now,
            "jti": to_encode.get("jti") or str(uuid.uuid4()),
            "type": token_type,
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """签发访问令牌。"""
    return encode(
        data,
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        ACCESS_TOKEN_TYPE,
    )


def create_refresh_token(data: dict[str, Any]) -> str:
    """签发刷新令牌。"""
    return encode(data, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), REFRESH_TOKEN_TYPE)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """解码并校验 JWT，失败抛 401。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers=CREDENTIALS_HEADERS,
        ) from None

    if expected_type is not None and payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌类型错误",
            headers=CREDENTIALS_HEADERS,
        )
    return payload


def verify_token(token: str, expected_type: str | None = ACCESS_TOKEN_TYPE) -> dict[str, Any]:
    """``decode_token`` 的别名，默认要求访问令牌。"""
    return decode_token(token, expected_type)


def remaining_ttl(payload: dict[str, Any]) -> int:
    """令牌剩余有效秒数（用于写黑名单时的 TTL）。"""
    exp = payload.get("exp")
    if not exp:
        return 0
    return max(int(exp - datetime.now(UTC).timestamp()), 0)


def subject_of(payload: dict[str, Any]) -> int:
    """从载荷里取出用户 id，取不到抛 401。"""
    try:
        return int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers=CREDENTIALS_HEADERS,
        ) from None


__all__ = [
    "ACCESS_TOKEN_TYPE",
    "CREDENTIALS_HEADERS",
    "REFRESH_TOKEN_TYPE",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "encode",
    "remaining_ttl",
    "subject_of",
    "verify_token",
]
