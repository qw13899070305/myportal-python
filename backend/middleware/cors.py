"""支持内网来源的 CORS 中间件（独立零件）。

在 Starlette 自带的 ``CORSMiddleware`` 基础上只改一件事：
**除了显式白名单，还放行"本机 / 内网"来源**。

为什么必须这样：用户从内网访问前端时，浏览器发来的 ``Origin`` 是
``http://192.168.1.2:5173`` 或 ``http://[2409:...]:5173``，
这些地址不可能提前写进 ``CORS_ORIGINS``。
判定规则见 :mod:`backend.core.network`（核心是"该地址属于本机"）。
"""

from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.network import is_local_origin


class LanCORSMiddleware(CORSMiddleware):
    """允许本机 / 内网来源的 CORS 中间件。"""

    def is_allowed_origin(self, origin: str) -> bool:
        if super().is_allowed_origin(origin):
            return True
        if not settings.ALLOW_PRIVATE_NETWORK_ORIGINS:
            return False
        return is_local_origin(origin)


def build_cors_middleware() -> type[CORSMiddleware]:
    """给 ``app.add_middleware`` 用的中间件类。"""
    return LanCORSMiddleware


__all__ = ["LanCORSMiddleware", "build_cors_middleware"]
