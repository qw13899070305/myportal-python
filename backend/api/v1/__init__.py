from fastapi import APIRouter
from backend.api.v1 import auth, users, files, share, trash, articles, admin, audit, notifications, chat_api, comments, withdraw, article_delete

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(files.router)
api_router.include_router(share.router)
api_router.include_router(trash.router)
api_router.include_router(articles.router)
api_router.include_router(admin.router)
api_router.include_router(audit.router)
api_router.include_router(notifications.router)
api_router.include_router(chat_api.router)
api_router.include_router(comments.router)
api_router.include_router(withdraw.router)
api_router.include_router(article_delete.router)
