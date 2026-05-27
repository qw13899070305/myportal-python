from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.core.config import settings
from backend.core.logger import logger
from backend.middleware.request_id import RequestIDMiddleware
from backend.handlers.error_handler import global_exception_handler, http_exception_handler
from backend.api.v1 import router as v1_router

app = FastAPI(title=settings.APP_NAME, version="1.0.0", debug=settings.DEBUG)

# 限流器初始化
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求追踪 ID
app.add_middleware(RequestIDMiddleware)

# 请求体大小限制 (50MB)
class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 50 * 1024 * 1024:
            return JSONResponse(status_code=413, content={"detail": "请求体过大"})
        return await call_next(request)

app.add_middleware(MaxBodySizeMiddleware)

# 异常处理
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# 注册路由
app.include_router(v1_router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    from backend.models.user import Base
    from backend.core.database import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("MyPortal 启动成功")

@app.on_event("shutdown")
async def shutdown():
    from backend.core.redis import close_redis
    await close_redis()
    logger.info("MyPortal 已关闭")

@app.get("/health")
async def health():
    return {"status": "ok"}