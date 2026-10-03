"""认证接口（组装配件）。

本模块**只负责组合**，每个子零件都可以单独摘掉：

=========================  ==========================================
模块                        接口
=========================  ==========================================
``auth_register.py``       POST /register
``auth_login.py``          POST /login, POST /token
``auth_token.py``          POST /refresh, POST /logout
``auth_profile.py``        GET  /me, POST /change-password, GET /check-username
``auth_captcha.py``        GET  /captcha
``auth_avatar.py``         POST/GET/DELETE /avatar
``auth_csrf.py``           GET  /csrf-token
=========================  ==========================================

公共逻辑在 :mod:`backend.api.v1.auth_common`。
把某个文件删掉只会少掉对应接口，其余认证功能照常工作。
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.v1._loader import include_optional
from backend.api.v1.auth_common import (  # noqa: F401  对外转发
    AUTH_HEADERS,
    issue_tokens,
    parse_login_request,
    perform_login,
)

router = APIRouter()

#: 组内的子零件：缺任何一个都只记日志，不影响其它接口
PARTS: list[tuple[str, str, list[str]]] = [
    ("backend.api.v1.auth_register", "", ["认证"]),
    ("backend.api.v1.auth_login", "", ["认证"]),
    ("backend.api.v1.auth_token", "", ["认证"]),
    ("backend.api.v1.auth_profile", "", ["认证"]),
    ("backend.api.v1.auth_captcha", "", ["认证-验证码"]),
    ("backend.api.v1.auth_avatar", "", ["认证-头像"]),
    ("backend.api.v1.auth_csrf", "", ["认证-CSRF"]),
]

for _module, _prefix, _tags in PARTS:
    include_optional(router, _module, _prefix, _tags)

__all__ = [
    "AUTH_HEADERS",
    "PARTS",
    "issue_tokens",
    "parse_login_request",
    "perform_login",
    "router",
]
