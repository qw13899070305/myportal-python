"""JWT 令牌黑名单（退出登录 / 刷新令牌轮换）。

Redis 可用时写入 Redis；未启用 Redis 时退化为进程内字典，
单进程部署下"退出登录立即失效"依然有效。
"""

import time

from backend.core.redis import get_redis, mark_unreachable

# 进程内降级存储：jti -> 过期时间戳
_local_blacklist: dict[str, float] = {}


def _purge_local() -> None:
    now = time.time()
    for jti in [k for k, exp in _local_blacklist.items() if exp <= now]:
        _local_blacklist.pop(jti, None)


async def add_token_to_blacklist(jti: str, expire_seconds: int) -> None:
    """把令牌加入黑名单，``expire_seconds`` 为剩余有效期。"""
    if not jti or expire_seconds <= 0:
        return
    redis = await get_redis()
    if redis is None:
        _purge_local()
        _local_blacklist[jti] = time.time() + expire_seconds
        return
    try:
        await redis.setex(f"blacklist:{jti}", expire_seconds, "1")
    except Exception:
        # Redis 抖动不应导致退出登录返回 500
        mark_unreachable()
        _purge_local()
        _local_blacklist[jti] = time.time() + expire_seconds


async def is_token_blacklisted(jti: str) -> bool:
    """令牌是否已被吊销。"""
    if not jti:
        return False
    redis = await get_redis()
    if redis is None:
        _purge_local()
        return jti in _local_blacklist
    try:
        return await redis.get(f"blacklist:{jti}") is not None
    except Exception:
        mark_unreachable()
        _purge_local()
        return jti in _local_blacklist


def reset_local_blacklist() -> None:
    """清空进程内黑名单（测试用）。"""
    _local_blacklist.clear()
