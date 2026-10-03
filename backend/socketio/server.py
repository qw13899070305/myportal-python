"""socket.io 服务实例。

单独放一个模块，是为了让事件扩展能够 ``from backend.socketio.server import sio``
而不必反向 import :mod:`backend.socketio.handlers`（那会形成循环依赖）。
"""

from __future__ import annotations

import os

import socketio

from backend.core.config import settings
from backend.core.logger import logger
from backend.core.network import origin_is_allowed
from backend.core.redis import redis_reachable

# 从环境变量读取允许的源；没配就跟主应用的 CORS 保持一致，避免两处漂移
_env_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
if _env_origins:
    allowed_origins = [o.strip() for o in _env_origins.split(",") if o.strip()]
else:
    allowed_origins = list(settings.CORS_ORIGINS)

if "*" in allowed_origins:
    raise ValueError("出于安全考虑，不允许使用通配符作为 CORS 来源")


def origin_allowed(origin, environ=None):
    """socket.io 的 Origin 判定（engineio 支持传可调用对象）。

    除了显式白名单，还放行本机 / 内网来源 —— 否则从
    ``http://192.168.1.2:5173`` 或 ``http://[2409:...]:5173``
    打开的页面，聊天握手会被 engineio 直接拒掉。
    """
    if not settings.ALLOW_PRIVATE_NETWORK_ORIGINS:
        return origin in allowed_origins
    return origin_is_allowed(origin, allowed_origins)


def _resolve_redis_url() -> str:
    """决定 socket.io 要不要用 Redis 管理器。

    只看 ``REDIS_ENABLED`` 是不够的 —— 配置写了 true 但 Redis 没起来时，
    ``AsyncRedisManager`` 构造不会报错，而是**运行期一直重连并刷日志**，
    同时多端广播会失败。所以这里先做一次真实的连通性探测。
    """
    if not settings.REDIS_ENABLED:
        return ""
    candidate = os.getenv("REDIS_URL", "").strip() or settings.REDIS_URL.strip()
    if not candidate:
        return ""
    if not redis_reachable():
        logger.warning(
            "socket.io 未使用 Redis 管理器（Redis 连不上），"
            "退回单机模式：多副本部署时不同进程间不会互通消息"
        )
        return ""
    return candidate


_redis_url = _resolve_redis_url()


def _create_server() -> socketio.AsyncServer:
    """Redis 可用时用 Redis 管理器（支持多副本），否则单机模式。"""
    if not _redis_url:
        return socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=origin_allowed)
    try:
        manager = socketio.AsyncRedisManager(_redis_url)
        return socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins=origin_allowed,
            client_manager=manager,
        )
    except Exception as exc:  # pragma: no cover - Redis 不可用时降级
        logger.warning(f"socket.io 使用 Redis 管理器失败，退回单机模式: {exc}")
        return socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=origin_allowed)


sio = _create_server()

__all__ = ["allowed_origins", "origin_allowed", "sio"]
