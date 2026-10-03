"""后台管理接口（统计 / 概览）。

子功能已经拆成可以单独摘掉的扩展件：

- :mod:`backend.api.v1.admin_users`    —— 用户管理
- :mod:`backend.api.v1.admin_chat`     —— 聊天管理
- :mod:`backend.api.v1.admin_config`   —— 站点配置 / 站点公开信息
- :mod:`backend.api.v1.admin_cleanup`  —— 回收站清理
- :mod:`backend.api.v1.audit`          —— 审计日志

本文件只保留数据统计与旧版 dashboard 入口。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import RoleChecker
from backend.models.article import STATUS_PENDING, Article
from backend.models.chat import ChatMessage
from backend.models.file import FileItem
from backend.models.user import User

router = APIRouter()

admin_only = RoleChecker(["admin", "super_admin"])


async def _collect_stats(db: AsyncSession) -> dict[str, int]:
    """统计各模块数量。"""
    users = await db.scalar(select(func.count()).select_from(User)) or 0
    articles = await db.scalar(select(func.count()).select_from(Article)) or 0
    pending = (
        await db.scalar(
            select(func.count()).select_from(Article).where(Article.status == STATUS_PENDING)
        )
        or 0
    )
    files = (
        await db.scalar(
            select(func.count()).select_from(FileItem).where(FileItem.deleted.is_(False))
        )
        or 0
    )
    trashed = (
        await db.scalar(
            select(func.count()).select_from(FileItem).where(FileItem.deleted.is_(True))
        )
        or 0
    )
    messages = await db.scalar(select(func.count()).select_from(ChatMessage)) or 0

    return {
        "users": users,
        "articles": articles,
        "pending_articles": pending,
        "files": files,
        "trashed_files": trashed,
        "chat_messages": messages,
    }


@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
):
    """后台仪表盘统计。"""
    return await _collect_stats(db)


@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
):
    """兼容旧接口：``GET /admin/dashboard``（``{code, data}`` 信封）。"""
    data = await _collect_stats(db)
    return {"code": 200, "data": data, **data}
