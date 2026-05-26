from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.config import settings
from backend.core.database import get_db  # 复用 API 层数据库会话
from backend.core.auth.jwt import verify_token
from backend.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    从 JWT 中获取当前用户，使用 API 层的数据库会话，
    避免双重会话问题。
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
        )
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户标识",
        )

    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id_int)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user


async def get_current_user_ws(token: str) -> User:
    """
    WebSocket 专用的用户获取函数，不依赖 HTTP 依赖注入，
    需要手动传入数据库会话。
    """
    from backend.core.database import AsyncSessionLocal
    payload = verify_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise ValueError("无效的令牌")
    try:
        user_id_int = int(user_id)
    except ValueError:
        raise ValueError("无效的用户ID")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).options(selectinload(User.roles)).where(User.id == user_id_int)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("用户不存在")
        return user