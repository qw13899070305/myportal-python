from backend.api.v1 import search_api
from fastapi import APIRouter
from backend.api.v1 import auth, files, chat, categories, admin_cleanup, notifications, health, articles

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(files.router)
api_router.include_router(chat.router)
api_router.include_router(categories.router)
api_router.include_router(admin_cleanup.router)
api_router.include_router(notifications.router)
api_router.include_router(health.router)
api_router.include_router(articles.router)
api_router.include_router(search_api.router)
