import redis.asyncio as aioredis
from backend.core.config import settings

_redis = None

async def get_redis():
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        except Exception:
            return None
    return _redis
