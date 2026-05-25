import os, socketio
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import select
from backend.core.config import settings
from backend.core.database import engine, Base, AsyncSessionLocal
from backend.core.security import SecurityMiddleware
from backend.core.rate_limit import RateLimiter
from backend.api.v1 import api_router
from backend.socketio import socket_app
from backend.models.config import SiteConfig

rate_limiter = RateLimiter(requests=120, window=60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as db:
        for key, val in [("site_name","myportal-python"), ("announcement","欢迎使用")]:
            existing = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
            if not existing.scalar_one_or_none():
                db.add(SiteConfig(key=key, value=val))
        await db.commit()
    yield
    await engine.dispose()

def create_app():
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None
    )

    # ✅ 修复 CORS 通配符+凭据冲突
    allow_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if "*" in allow_origins and os.getenv("ALLOW_CREDENTIALS", "true").lower() == "true":
        raise ValueError("❌ CORS 不允许在 allow_credentials=True 时使用通配符 *")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityMiddleware)

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if request.url.path.startswith("/api") or request.url.path.startswith("/ws"):
            rate_limiter(request)
        return await call_next(request)

    # ✅ 全局异常处理增加日志（后续可接入 logging）
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        print(f"❌ 未捕获异常 [{request.method} {request.url.path}]: {exc}")
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})

    app.include_router(api_router, prefix="/api/v1")
    app.mount("/ws", socket_app)

    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
    if os.path.isdir(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app

app = create_app()
