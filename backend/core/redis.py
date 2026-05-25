import redis.asyncio as aioredis
from backend.core.config import settings

_redis = None

async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10,
            health_check_interval=30,
            retry_on_timeout=True,
            socket_keepalive=True,
        )
    return _redis
