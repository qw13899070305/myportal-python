"""认证相关的统一入口（转发模块）。

历史遗留代码里有多个认证模块平行存在，现在全部指向
:mod:`backend.core.security`，这里聚合成一个稳定的导入入口。
"""

from backend.core.security import (  # noqa: F401
    RoleChecker,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    get_current_user_flexible,
    get_current_user_optional,
    is_admin,
    load_user_from_token,
    oauth2_scheme,
    oauth2_scheme_optional,
    verify_token,
)

__all__ = [
    "RoleChecker",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_current_user",
    "get_current_user_flexible",
    "get_current_user_optional",
    "is_admin",
    "load_user_from_token",
    "oauth2_scheme",
    "oauth2_scheme_optional",
    "verify_token",
]
