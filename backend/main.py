from fastapi import FastAPI, Request
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

# 速率限制器（尝试 Redis，失败时使用内存）
try:
    redis_storage = RedisStorage(settings.REDIS_URL)
    limiter = Limiter(key_func=get_remote_address, storage=redis_storage)
    logger.info("✅ 速率限制器使用 Redis 存储")
except Exception:
    limiter = Limiter(key_func=get_remote_address)
    logger.warning("⚠️ Redis 不可用，速率限制器使用内存存储")

app = FastAPI(title="MyPortal", docs_url="/docs" if settings.DEBUG else None, redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda req, exc: JSONResponse(status_code=429, content={"detail": "请求过于频繁，请稍后重试"}))

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@CsrfProtect.load_config
def get_csrf_config():
    return [("fastapi_csrf_protect", settings.SECRET_KEY)]

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' ws: wss:"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# 仅捕获 HTTPException 和 CsrfProtectError，让系统异常自然暴露
from fastapi import HTTPException as FastAPIHTTPException

@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    logger.warning(f"HTTP {exc.status_code}: {request.method} {request.url.path} - {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})

@app.exception_handler(CsrfProtectError)
async def csrf_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(status_code=403, content={"detail": "CSRF 验证失败"})

# 兜底：记录未预料的异常但不吞掉堆栈
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常: {request.method} {request.url.path}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试"})

app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
