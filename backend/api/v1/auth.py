from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import create_access_token, get_current_user
from backend.models.user import User
from backend.schemas.user import UserOut, UserCreate, UserLogin
from backend.services.user_service import create_user, authenticate_user

router = APIRouter(prefix="/auth", tags=["认证"])

def set_token_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        path="/"
    )

@router.post("/register", response_model=UserOut)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    return await create_user(db, user_in)

@router.post("/login")
async def login(response: Response, login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(401, "用户名或密码错误")
    token = create_access_token(data={"sub": user.username, "user_id": user.id})
    set_token_cookie(response, token)
    return {"message": "登录成功", "user": UserOut.from_orm(user)}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"message": "已登出"}

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/switch-role")
async def switch_role(
    response: Response,
    role_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from backend.services.user_service import switch_user_role
    user = await switch_user_role(db, current_user, role_name)
    if not user:
        raise HTTPException(400, "角色切换失败")
    token = create_access_token(data={"sub": user.username, "user_id": user.id})
    set_token_cookie(response, token)
    return {"message": f"已切换为 {role_name}", "user": UserOut.from_orm(user)}
