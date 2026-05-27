from fastapi import APIRouter
from backend.api.v1 import auth, users, files, articles, chat, admin

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(users.router, prefix="/users", tags=["用户"])
router.include_router(files.router, prefix="/files", tags=["文件"])
router.include_router(articles.router, prefix="/articles", tags=["文章"])
router.include_router(chat.router, prefix="/chat", tags=["聊天"])
router.include_router(admin.router, prefix="/admin", tags=["管理"])