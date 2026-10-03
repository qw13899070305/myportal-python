"""审计日志查询（仅管理员）。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import RoleChecker
from backend.models.audit import AuditLog

router = APIRouter(dependencies=[Depends(RoleChecker(["admin", "super_admin"]))])


@router.get("/")
async def list_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=settings.PAGE_SIZE_MAX),
    action: str = Query("", max_length=100),
    user_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """分页查询审计日志，支持按动作与操作者过滤。"""
    conditions = []
    if action.strip():
        conditions.append(AuditLog.action.ilike(f"%{action.strip()}%"))
    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)

    stmt = select(AuditLog).where(*conditions)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    result = await db.execute(
        stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = result.scalars().all()
    return {
        "total": total,
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.user.username if log.user else None,
                "action": log.action,
                "detail": log.detail,
                "ip": log.ip_address,
                "ip_address": log.ip_address,
                "time": log.created_at,
                "created_at": log.created_at,
            }
            for log in items
        ],
    }
