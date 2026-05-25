from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from jwt import PyJWTError
from datetime import datetime, timedelta
import uuid
import logging

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.redis import get_redis
from backend.models.user import User

logger = logging.getLogger("myportal.security")

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], options={"verify_exp": True})
    except PyJWTError:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")

async def is_token_blacklisted(jti: str) -> bool:
    try:
        redis = await get_redis()
        if redis:
            return await redis.exists(f"blacklist:{jti}")
        else:
            logger.error("Redis 不可用，无法查询 token 黑名单")
            return False
    except Exception as e:
        logger.error(f"查询 token 黑名单失败: {e}")
        return False

async def add_token_to_blacklist(jti: str, expire_seconds: int):
    try:
        redis = await get_redis()
        if redis:
            await redis.setex(f"blacklist:{jti}", expire_seconds, "1")
        else:
            logger.error("Redis 不可用，无法将 token 加入黑名单")
    except Exception as e:
        logger.error(f"Token 黑名单写入失败: {e}")

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    payload = verify_token(token)
    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        raise HTTPException(status_code=401, detail="令牌已失效")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="令牌无效")
    from backend.services.user_service import get_user_by_username
    user = await get_user_by_username(db, username)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user

class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
    async def __call__(self, current_user: User = Depends(get_current_user)):
        if not any(role.name in self.allowed_roles for role in current_user.roles):
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return current_user
