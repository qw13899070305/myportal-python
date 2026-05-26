import logging
from fastapi import HTTPException, status
from backend.core.config import settings

logger = logging.getLogger(__name__)


async def add_token_to_blacklist(jti: str, expire_seconds: int):
    """将 JWT 的唯一标识加入 Redis 黑名单"""
    if not settings.REDIS_ENABLED:
        return
    try:
        import redis.asyncio as aioredis
        redis = aioredis.from_url(settings.REDIS_URL)
        await redis.setex(f"blacklist:{jti}", expire_seconds, "1")
        await redis.close()
    except Exception as e:
        # 不要记录 jti 等敏感信息
        logger.error("添加 token 到黑名单失败")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="认证服务暂时不可用"
        )


async def is_token_blacklisted(jti: str) -> bool:
    """检查 JWT 是否在黑名单中"""
    if not settings.REDIS_ENABLED:
        return False
    try:
        import redis.asyncio as aioredis
        redis = aioredis.from_url(settings.REDIS_URL)
        result = await redis.get(f"blacklist:{jti}")
        await redis.close()
        return result is not None
    except Exception as e:
        logger.error("查询 token 黑名单失败")
        # 生产环境或调试模式都不应直接放行
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="认证服务暂时不可用"
        )