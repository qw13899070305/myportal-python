"""socket.io 握手阶段的令牌解析。"""

from __future__ import annotations

import jwt

from backend.core.config import settings

#: 允许的令牌类型（``None`` 是为了兼容早期没有 type 字段的令牌）
_ALLOWED_TOKEN_TYPES = {None, "access"}


def extract_token(environ: dict, auth: dict | None = None) -> str | None:
    """依次从 auth 载荷、Authorization 头、``?token=`` 查询参数里取令牌。"""
    if isinstance(auth, dict):
        token = auth.get("token") or auth.get("Authorization")
        if token:
            return str(token).replace("Bearer ", "").strip()

    header = environ.get("HTTP_AUTHORIZATION", "")
    if header:
        return header.replace("Bearer ", "").strip()

    query = environ.get("QUERY_STRING", "")
    for part in query.split("&"):
        if part.startswith("token="):
            return part[len("token=") :]
    return None


def decode_user_id(token: str) -> int:
    """校验访问令牌并返回用户 id；失败抛 ``jwt`` 异常。"""
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub"]},
    )
    if payload.get("type") not in _ALLOWED_TOKEN_TYPES:
        raise jwt.InvalidTokenError("令牌类型错误")
    return int(payload["sub"])


__all__ = ["decode_user_id", "extract_token"]
