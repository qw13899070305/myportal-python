from fastapi import APIRouter
from backend.api.v1.auth import router as auth_router
from backend.api.v1.articles import router as articles_router
from backend.api.v1.chat import router as chat_router
from backend.api.v1.files import router as files_router
from backend.api.v1.admin import router as admin_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["认证"])
router.include_router(articles_router, prefix="/articles", tags=["文章"])
router.include_router(chat_router, prefix="/chat", tags=["聊天"])
router.include_router(files_router, prefix="/files", tags=["文件"])
router.include_router(admin_router, prefix="/admin", tags=["管理"])