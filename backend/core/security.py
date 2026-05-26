from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from jwt import PyJWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.models.user import User
from sqlalchemy import select
from sqlalchemy.orm import selectinload
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
    except PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = verify_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
        return user

async def add_token_to_blacklist(jti: str, expire_seconds: int):
    if not settings.REDIS_ENABLED:
        return
    try:
        import redis.asyncio as aioredis
        redis = aioredis.from_url(settings.REDIS_URL)
        await redis.setex(f"blacklist:{jti}", expire_seconds, "1")
        await redis.close()
    except Exception as e:
        logger.error(f"添加 token 到黑名单失败: {e}")
        # 注意：这里不抛出异常，因为黑名单只是附加安全措施，不应该阻止登录流程
        # 但在生产环境中应监控此失败

async def is_token_blacklisted(jti: str) -> bool:
    if not settings.REDIS_ENABLED:
        return False
    try:
        import redis.asyncio as aioredis
        redis = aioredis.from_url(settings.REDIS_URL)
        result = await redis.get(f"blacklist:{jti}")
        await redis.close()
        return result is not None
    except Exception as e:
        logger.error(f"查询 token 黑名单失败: {e}")
        # 安全策略：如果无法验证黑名单，生产环境应拒绝
        if not settings.DEBUG:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务暂时不可用")
        return False

class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)):
        # 由于 get_current_user 已经使用 selectinload 加载了 roles，这里直接检查
        if not current_user.roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有分配角色")
        if not any(role.name in self.allowed_roles for role in current_user.roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return current_user