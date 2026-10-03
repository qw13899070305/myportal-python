"""FastAPI 应用入口。

这里只做**组装**，具体能力都在各自的模块里，可以单独摘掉：

===============================================  ==================================
模块                                              职责
===============================================  ==================================
:mod:`backend.core.bootstrap`                     内置角色 / 初始管理员
:mod:`backend.core.rate_limit`                    全局限流器
:mod:`backend.middleware.request_id`              请求追踪 ID
:mod:`backend.middleware.max_body`                请求体大小限制
:mod:`backend.handlers.error_handler`             统一异常响应
:mod:`backend.api.v1`                             业务路由（27 个模块的可选聚合）
:mod:`backend.socketio.mount`                     socket.io 实时通信
:mod:`backend.spa`                                前端静态资源 + history 回退
===============================================  ==================================
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from fastapi_csrf_protect.exceptions import CsrfProtectError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.api.v1 import router as v1_router
from backend.core.bootstrap import bootstrap
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal, engine, init_models
from backend.core.logger import logger
from backend.core.network import log_listening
from backend.core.rate_limit import limiter
from backend.core.redis import close_redis, ping_redis
from backend.handlers.error_handler import (
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from backend.middleware.cors import LanCORSMiddleware
from backend.middleware.max_body import MaxBodySizeMiddleware
from backend.middleware.request_id import RequestIDMiddleware
from backend.services.search import close_search_client
from backend.socketio.mount import mount_socketio
from backend.spa import mount_frontend


@asynccontextmanager
async def lifespan(_: FastAPI):
    """启动时建表 + 引导数据，关闭时释放连接。"""
    await init_models()
    await bootstrap()
    logger.info(
        f"{settings.APP_NAME} 启动完成"
        f"（DEBUG={settings.DEBUG}, Redis={'on' if settings.REDIS_ENABLED else 'off'}）"
    )
    # 把内网可访问地址打进日志，省得去猜 IP
    log_listening(settings.PORT)
    yield
    await close_redis()
    await close_search_client()
    await engine.dispose()
    logger.info(f"{settings.APP_NAME} 已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    # 框架级 debug 始终关闭：生产环境不能把 traceback 暴露给客户端
    debug=False,
    lifespan=lifespan,
)

# ---------------- 限流 ----------------
# 必须是全局同一个 limiter 实例，否则限流不生效
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------- CORS ----------------
# 用 LanCORSMiddleware：除白名单外，还放行本机/内网来源，
# 否则从 192.168.x.x 或 [2409:...] 打开的页面会被 CORS 拦住
app.add_middleware(
    LanCORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
    expose_headers=["X-Request-ID", "X-Captcha-Id"],
)

# ---------------- 自定义中间件 ----------------
app.add_middleware(MaxBodySizeMiddleware)
app.add_middleware(RequestIDMiddleware)


# ---------------- 异常处理 ----------------


async def csrf_exception_handler(request: Request, exc: CsrfProtectError) -> JSONResponse:
    """CSRF 校验失败统一返回 403，并给出可读提示。"""
    message = getattr(exc, "message", None) or str(exc)
    logger.warning(f"CSRF 校验失败 {request.method} {request.url.path}: {message}")
    return JSONResponse(status_code=403, content={"detail": f"CSRF 校验失败：{message}"})


app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(CsrfProtectError, csrf_exception_handler)

# ---------------- 业务路由 ----------------
app.include_router(v1_router, prefix="/api/v1")

# ---------------- 实时通信 ----------------
mount_socketio(app)


@app.get("/health", tags=["健康检查"])
async def health():
    """健康检查：包含数据库、Redis、可访问地址与已加载的扩展。"""
    from sqlalchemy import text

    from backend.core.network import local_urls
    from backend.extensions import describe_registries

    db_ok = False
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # pragma: no cover - 仅在异常时进入
        logger.error(f"健康检查数据库失败: {exc}")

    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "redis": await ping_redis() if settings.REDIS_ENABLED else "disabled",
        # 内网访问时用得上：直接列出可以从哪些地址访问
        "access_urls": local_urls(settings.PORT),
        "extensions": describe_registries(),
    }


# ---------------- 前端静态资源 ----------------
# 必须最后挂载：前面的 API 路由优先级更高，不会被静态资源吞掉
mount_frontend(app)
