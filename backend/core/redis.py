"""Redis 连接（**可选依赖**）。

设计原则：**Redis 挂了不能影响任何功能**。

- 未配置 / 连不上时所有函数返回 ``None``，调用方走进程内降级
- 带缓存的 TCP 探测，避免"每次请求都去连一次挂掉的 Redis"
  （既有延迟，又会把日志刷爆）
- 状态变化时才打日志，不重复刷

注意 ``REDIS_ENABLED=true`` 只代表"想用"，不代表"能用"——
真正的判据是 :func:`redis_reachable`。
"""

from __future__ import annotations

import socket
import time
from urllib.parse import urlparse

import redis.asyncio as aioredis

from backend.core.config import settings
from backend.core.logger import logger

_client: aioredis.Redis | None = None

#: TCP 探测结果缓存 (时间戳, 是否可达)
_probe_cache: tuple[float, bool] = (0.0, False)
#: 探测缓存有效期（秒）
PROBE_TTL = 15.0
#: 探测超时（秒）
PROBE_TIMEOUT = 0.5

#: 上一次记录的状态，用于"只在状态变化时打日志"
_last_state: bool | None = None


def _parse_host_port(url: str) -> tuple[str, int]:
    """从 redis://[:pass@]host:port/db 里取出 host 与 port。"""
    parsed = urlparse(url)
    return parsed.hostname or "localhost", parsed.port or 6379


def redis_configured() -> bool:
    """配置上是否启用了 Redis。"""
    return bool(settings.REDIS_ENABLED and settings.REDIS_URL.strip())


def redis_reachable(timeout: float = PROBE_TIMEOUT) -> bool:
    """Redis 是否真的连得上（TCP 层探测，结果缓存 ``PROBE_TTL`` 秒）。

    这是同步函数，供启动期决策使用（例如 socket.io 选哪个 manager）
    以及给 :func:`get_redis` 做前置判断。
    """
    global _probe_cache, _last_state

    if not redis_configured():
        return False

    now = time.monotonic()
    if now - _probe_cache[0] < PROBE_TTL:
        return _probe_cache[1]

    host, port = _parse_host_port(settings.REDIS_URL)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            reachable = True
    except OSError:
        reachable = False

    _probe_cache = (now, reachable)

    # 只在状态变化时提示，避免刷屏
    if _last_state is not reachable:
        if reachable:
            logger.info(f"Redis 已连接: {host}:{port}")
        else:
            logger.warning(
                f"Redis 配置为启用但连不上（{host}:{port}），"
                "相关功能将降级为进程内存储（单进程部署不受影响）"
            )
        _last_state = reachable

    return reachable


async def get_redis() -> aioredis.Redis | None:
    """返回全局 Redis 客户端；未配置或连不上时返回 None。

    连不上时**不会**抛出异常，调用方只需处理 ``None``（走降级分支）。
    """
    global _client
    if not redis_configured() or not redis_reachable():
        return None
    if _client is None:
        _client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_POOL_SIZE,
            socket_connect_timeout=PROBE_TIMEOUT,
            socket_timeout=2,
        )
    return _client


async def close_redis() -> None:
    """关闭连接池（应用 shutdown 时调用）。"""
    global _client
    if _client is not None:
        # redis>=5 使用 aclose()，close() 已废弃
        await _client.aclose()
        _client = None


async def ping_redis() -> bool:
    """健康检查用：Redis 可用返回 True。"""
    client = await get_redis()
    if client is None:
        return False
    try:
        await client.ping()
        return True
    except Exception:
        # 运行期掉线：让下次探测重新判断
        mark_unreachable()
        return False


def mark_unreachable() -> None:
    """运行期发现 Redis 掉线时调用：立即进入降级并让下次重新探测。"""
    global _probe_cache, _last_state
    _probe_cache = (0.0, False)
    if _last_state is not False:
        logger.warning("Redis 连接中断，降级为进程内存储")
        _last_state = False


def reset_probe_cache() -> None:
    """清空探测缓存（测试用）。"""
    global _probe_cache, _last_state
    _probe_cache = (0.0, False)
    _last_state = None


def status() -> dict:
    """Redis 配置与连通性概况（供健康检查展示）。"""
    return {
        "configured": redis_configured(),
        "reachable": redis_reachable(),
        "url": settings.REDIS_URL if redis_configured() else "",
    }
