from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.core.database import get_db
from backend.core.security import RoleChecker, get_current_user
from backend.models.user import User
from backend.schemas.user import UserOut
from typing import List

router = APIRouter()

admin_only = RoleChecker(["admin"])


@router.get("/users", response_model=List[UserOut])
async def list_users(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    total = await db.scalar(select(func.count()).select_from(User))
    stmt = select(User).offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users