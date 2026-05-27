from fastapi import APIRouter, Depends, HTTPException
from backend.core.security import get_current_user, RoleChecker
from backend.models.user import User, get_user_by_id, get_user_by_username
from backend.core.database import AsyncSession, get_db
from sqlalchemy.future import select

router = APIRouter()

@router.get("/")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(RoleChecker(["admin"]))
):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return {"code": 200, "data": [{"id": u.id, "username": u.username, "email": u.email} for u in users]}

@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "data": {"id": user.id, "username": user.username, "email": user.email}}