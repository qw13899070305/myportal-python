from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.core.config import settings

# 创建应用
app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

# 限流器
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from backend.api.v1.auth import router as auth_router
from backend.api.v1.articles import router as articles_router
from backend.api.v1.chat import router as chat_router
from backend.api.v1.files import router as files_router
from backend.api.v1.admin import router as admin_router

app.include_router(auth_router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(articles_router, prefix="/api/v1/articles", tags=["文章"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["聊天"])
app.include_router(files_router, prefix="/api/v1/files", tags=["文件"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["管理"])

# 挂载静态文件（前端构建产物）
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    @app.get("/")
    async def root():
        return {"message": f"{settings.APP_NAME} 后端服务运行中，前端未构建或未挂载"}

# 健康检查
@app.get("/health")
async def health():
    return {"status": "ok"}