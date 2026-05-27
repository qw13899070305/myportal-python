from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from jwt import PyJWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.blacklist import is_token_blacklisted
from backend.models.user import User
import logging

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    payload = verify_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")

    # 始终检查黑名单（不再因 DEBUG 跳过）
    jti = payload.get("jti")
    if jti:
        if await is_token_blacklisted(jti):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌已失效")

    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id_int)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user

class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)):
        if not current_user.roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        user_roles = [role.name for role in current_user.roles]
        if not any(role in self.allowed_roles for role in user_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return True