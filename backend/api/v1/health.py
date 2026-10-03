"""健康检查（带数据库 / Redis 状态）。"""

from fastapi import APIRouter
from sqlalchemy import text

from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.core.logger import logger
from backend.core.redis import ping_redis
from backend.services.search import get_search_client

router = APIRouter()


@router.get("/")
async def health_check():
    """返回各依赖组件的健康状态。

    数据库不可用时返回 200 + ``status=degraded``，
    方便运维直接看到哪一部分出了问题。
    """
    db_ok = False
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # pragma: no cover - 仅在异常时进入
        logger.error(f"健康检查：数据库连接失败: {exc}")

    redis_state: str | bool = "disabled"
    if settings.REDIS_ENABLED:
        redis_state = await ping_redis()

    search_state: str | bool = "disabled"
    if settings.MEILISEARCH_URL:
        try:
            search_state = await get_search_client() is not None
        except Exception:
            search_state = False

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "database": db_ok,
        "redis": redis_state,
        "search": search_state,
    }
