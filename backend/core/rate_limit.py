"""限流。

本模块提供两种可用的限流方式：

1. :data:`limiter` —— slowapi 的全局限流器，``main.py`` 会把它注册到
   ``app.state.limiter``。用法::

       @router.post("/login")
       @limiter.limit("10/minute")
       async def login(request: Request, ...): ...

   **注意**：被装饰的函数签名里必须显式声明 ``request: Request``，
   否则 slowapi 在运行时会抛 ``Exception("No request argument found")``。
   它必须是全局同一个实例，否则限流状态不会生效。

2. :class:`RateLimiter` —— 轻量的进程内依赖式限流器，适合只给单个路由
   加限制::

       @router.get("/heavy", dependencies=[Depends(RateLimiter(5, 60))])
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.core.config import settings

#: 全局限流器（必须全局唯一）
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    enabled=settings.RATE_LIMIT_ENABLED,
)


def client_key(request: Request) -> str:
    """取客户端标识：优先 X-Forwarded-For，其次直连地址。"""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """进程内滑动窗口限流器，可作为依赖使用。

    局限：状态在进程内存中，多副本部署时每个副本各自计数。
    需要全局精确限流请使用 :data:`limiter`（或把后端换成 Redis）。
    """

    def __init__(self, requests: int = 60, window: int = 60):
        self.requests = requests
        self.window = window
        self.clients: dict[str, list[float]] = defaultdict(list)

    def __call__(self, request: Request) -> None:
        key = client_key(request)
        now = time.time()
        self.clients[key] = [t for t in self.clients[key] if now - t < self.window]
        if len(self.clients[key]) >= self.requests:
            raise HTTPException(
                status_code=429,
                detail="请求太频繁，请稍后再试",
                headers={"Retry-After": str(self.window)},
            )
        self.clients[key].append(now)

    def reset(self) -> None:
        """清空计数（测试或运维手动重置时使用）。"""
        self.clients.clear()
