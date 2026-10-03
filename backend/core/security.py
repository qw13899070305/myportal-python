"""认证与授权（对外门面）。

实现已经拆成三个可以单独替换的零件：

======================  ==================================================
模块                     职责
======================  ==================================================
``core/password.py``    密码哈希（Argon2）
``core/tokens.py``      JWT 签发 / 校验（纯函数，不碰数据库）
``core/current_user.py`` 从请求里解析当前用户（依赖注入）
``core/roles.py``       角色判定与权限依赖
======================  ==================================================

历史代码统一从本模块导入，因此这里是稳定的对外入口；
``core/jwt.py``、``core/auth.py``、``core/dependencies.py``、``core/permissions.py``
也都是指向这里的转发模块。
"""

from backend.core.current_user import (  # noqa: F401
    get_current_user,
    get_current_user_flexible,
    get_current_user_optional,
    load_user_from_token,
    oauth2_scheme,
    oauth2_scheme_optional,
)
from backend.core.password import (  # noqa: F401
    get_password_hash,
    needs_rehash,
    verify_password,
)
from backend.core.roles import (  # noqa: F401
    ADMIN_ROLES,
    RoleChecker,
    has_any_role,
    is_admin,
    roles_of,
)
from backend.core.tokens import (  # noqa: F401
    CREDENTIALS_HEADERS,
    create_access_token,
    create_refresh_token,
    decode_token,
    remaining_ttl,
    verify_token,
)

__all__ = [
    "ADMIN_ROLES",
    "CREDENTIALS_HEADERS",
    "RoleChecker",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_current_user",
    "get_current_user_flexible",
    "get_current_user_optional",
    "get_password_hash",
    "has_any_role",
    "is_admin",
    "load_user_from_token",
    "needs_rehash",
    "oauth2_scheme",
    "oauth2_scheme_optional",
    "remaining_ttl",
    "roles_of",
    "verify_password",
    "verify_token",
]
