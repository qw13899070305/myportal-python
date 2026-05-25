import os, socketio
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.database import engine, Base, AsyncSessionLocal
from backend.core.security import SecurityMiddleware
from backend.core.rate_limit import RateLimiter
from backend.api.v1 import api_router
from backend.socketio import socket_app

rate_limiter = RateLimiter(requests=120, window=60)

async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    from backend.models.user import User, Role
    from backend.models.config import SiteConfig
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
#             admin = User(username="admin")
#             admin.set_password("admin123")
#             for rname in ["reader","author","moderator","admin","super_admin","chat_user"]:
#                 r = await db.execute(select(Role).where(Role.name == rname))
                role = r.scalar_one_or_none()
                if not role:
                    role = Role(name=rname); db.add(role)
                admin.roles.append(role)
            db.add(admin)
            await db.commit()
        for key, val in [("site_name","myportal-python"), ("announcement","欢迎使用")]:
            existing = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
            if not existing.scalar_one_or_none():
                db.add(SiteConfig(key=key, value=val))
        await db.commit()
    yield
    await engine.dispose()

def create_app():
    app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan, docs_url="/docs" if settings.DEBUG else None)
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    app.add_middleware(SecurityMiddleware)

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if not request.url.path.startswith("/api") and not request.url.path.startswith("/ws"):
            return await call_next(request)
        rate_limiter(request)
        return await call_next(request)

    app.include_router(api_router, prefix="/api/v1")
    app.mount("/ws", socket_app)
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
    if os.path.isdir(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app
