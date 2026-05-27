import redis.asyncio as aioredis
from backend.core.config import settings

_redis_pool: aioredis.Redis | None = None

async def get_redis() -> aioredis.Redis | None:
    global _redis_pool
    if not settings.REDIS_ENABLED or not settings.REDIS_URL:
        return None
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.DB_POOL_SIZE,
        )
    return _redis_pool

async def close_redis():
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None