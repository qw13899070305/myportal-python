from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request, HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.storage.redis import RedisStorage
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
import logging
import sys

from backend.core.config import settings
from backend.api.v1 import api_router
from backend.core.database import engine, Base

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("myportal")

# 速率限制器：生产环境强制使用 Redis
if settings.DEBUG:
    limiter = Limiter(key_func=get_remote_address)
    logger.info("开发模式：使用内存限流")
else:
    try:
        redis_storage = RedisStorage(settings.REDIS_URL)
        limiter = Limiter(key_func=get_remote_address, storage=redis_storage)
        logger.info("生产模式：使用 Redis 限流")
    except Exception as e:
        logger.critical(f"生产环境无法连接 Redis 限流存储: {e}")
        sys.exit(1)

app = FastAPI(title="MyPortal", docs_url="/docs" if settings.DEBUG else None, redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda req, exc: JSONResponse(status_code=429, content={"detail": "请求过于频繁"}))

# CORS
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@CsrfProtect.load_config
def get_csrf_config():
    return [("fastapi_csrf_protect", settings.SECRET_KEY)]

# 安全头常量定义
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data: blob:; font-src 'self'; connect-src 'self' ws: wss:"
    ),
}

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# 异常处理：先处理具体异常，最后兜底时放过系统信号
@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    logger.warning(f"HTTP {exc.status_code}: {request.method} {request.url.path} - {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})

@app.exception_handler(CsrfProtectError)
async def csrf_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(status_code=403, content={"detail": "CSRF 验证失败"})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, (SystemExit, KeyboardInterrupt)):
        raise  # 允许程序正常退出
    logger.error(f"未处理异常: {request.method} {request.url.path}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})

# 路由
app.include_router(api_router, prefix="/api/v1")
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
