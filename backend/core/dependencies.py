"""FastAPI 依赖集合（转发模块）。

此前本模块从 ``backend.core.auth.jwt`` 导入，而 ``core/auth.py``
只是一个普通模块、并不是包，所以导入必然失败。现在统一指向
:mod:`backend.core.security`。
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import AsyncSessionLocal
from backend.core.security import (
    get_current_user,  # noqa: F401  对外转发
    get_current_user_flexible,  # noqa: F401
    get_current_user_optional,  # noqa: F401
    is_admin,  # noqa: F401
    load_user_from_token,
    oauth2_scheme,  # noqa: F401
    oauth2_scheme_optional,  # noqa: F401
)
from backend.models.user import User

__all__ = [
    "get_current_user",
    "get_current_user_flexible",
    "get_current_user_optional",
    "get_current_user_ws",
    "is_admin",
    "oauth2_scheme",
    "oauth2_scheme_optional",
]


async def get_current_user_ws(token: str, db: Optional[AsyncSession] = None) -> User:
    """WebSocket 专用：不依赖 HTTP 依赖注入，手动传入/新建数据库会话。

    校验失败抛 ``ValueError``，方便 WebSocket 端直接关闭连接。
    """
    try:
        if db is not None:
            return await load_user_from_token(token, db)
        async with AsyncSessionLocal() as session:
            user = await load_user_from_token(token, session)
            # 会话关闭后仍需要读用户名等已加载字段，这里显式加载一次
            await session.refresh(user, attribute_names=["roles"])
            return user
    except Exception as exc:
        raise ValueError(str(exc) or "无效的令牌") from None
