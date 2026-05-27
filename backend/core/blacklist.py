from fastapi import HTTPException, status
from backend.core.config import settings
from backend.core.redis import get_redis

async def add_token_to_blacklist(jti: str, expire_seconds: int):
    redis = await get_redis()
    if not redis:
        if settings.REDIS_ENABLED:
            raise HTTPException(status_code=503, detail="认证服务不可用")
        return
    await redis.setex(f"blacklist:{jti}", expire_seconds, "1")

async def is_token_blacklisted(jti: str) -> bool:
    redis = await get_redis()
    if not redis:
        if settings.REDIS_ENABLED:
            raise HTTPException(status_code=503, detail="认证服务不可用")
        return False
    return await redis.get(f"blacklist:{jti}") is not None