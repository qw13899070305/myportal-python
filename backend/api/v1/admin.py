from fastapi import APIRouter, Depends
from backend.core.security import get_current_user, RoleChecker

router = APIRouter()

@router.get("/dashboard")
async def dashboard(current_user = Depends(get_current_user), _: bool = Depends(RoleChecker(["admin"]))):
    return {"code": 200, "data": {"users": 100, "articles": 200}}