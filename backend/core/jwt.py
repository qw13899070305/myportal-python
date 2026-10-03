"""JWT 工具（转发模块）。

真正的实现在 :mod:`backend.core.security`，这里只做转发，
避免出现两套互不一致的令牌逻辑（此前本模块缺少 ``jti``，
导致令牌黑名单功能完全失效）。
"""

from datetime import timedelta
from typing import Any, Optional

from backend.core.security import (  # noqa: F401
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)

__all__ = [
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_token",
    "create_token_pair",
]


def create_token_pair(subject: str | int) -> tuple[str, str]:
    """一次性签发 (access_token, refresh_token)。

    两个令牌各自拥有独立的 ``jti``，刷新时只作废旧刷新令牌。
    """
    data: dict[str, Any] = {"sub": str(subject)}
    return create_access_token(data), create_refresh_token(data)


def access_token_expires_delta() -> Optional[timedelta]:
    """访问令牌有效期（默认从配置读取）。"""
    from backend.core.config import settings

    return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
