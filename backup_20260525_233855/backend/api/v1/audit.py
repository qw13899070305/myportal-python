from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.core.database import get_db
from backend.core.auth import RoleChecker
from backend.models.audit import AuditLog

router = APIRouter(prefix="/audit", tags=["审计"], dependencies=[Depends(RoleChecker(["admin","super_admin"]))])

@router.get("/")
async def list_logs(page: int=1, limit: int=20, db: AsyncSession = Depends(get_db)):
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    logs = await db.execute(q.offset((page-1)*limit).limit(limit))
    items = logs.scalars().all()
    return {"total":total, "items":[{"user_id":l.user_id,"action":l.action,"detail":l.detail,"ip":l.ip_address,"time":l.created_at} for l in items]}
