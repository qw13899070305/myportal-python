from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi_csrf_protect import CsrfProtect
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import create_access_token, get_current_user, verify_token, add_token_to_blacklist
from backend.models.user import User
from backend.schemas.user import UserOut, UserCreate, UserLogin
from backend.services.user_service import create_user, authenticate_user

router = APIRouter(prefix="/auth", tags=["认证"])
limiter = Limiter(key_func=get_remote_address)

def set_token_cookie(response: Response, token: str):
    response.set_cookie(key="access_token", value=token, httponly=True, secure=not settings.DEBUG, samesite="lax", max_age=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60), path="/")

@router.post("/register", response_model=UserOut)
@limiter.limit("3/minute")
async def register(request: Request, user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    return await create_user(db, user_in)

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, response: Response, login_data: UserLogin, db: AsyncSession = Depends(get_db), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    user = await authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(401, "用户名或密码错误")
    token = create_access_token(data={"sub": user.username, "user_id": user.id})
    set_token_cookie(response, token)
    return {"message": "登录成功", "user": UserOut.from_orm(user)}

@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = verify_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                ttl = max(0, int(exp - datetime.now(timezone.utc).timestamp()))
                await add_token_to_blacklist(jti, ttl)
        except Exception:
            pass
    response.delete_cookie("access_token", path="/")
    return {"message": "已登出"}

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/switch-role")
@limiter.limit("10/minute")
async def switch_role(request: Request, response: Response, role_name: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    from backend.services.user_service import switch_user_role
    user = await switch_user_role(db, current_user, role_name)
    if not user:
        raise HTTPException(400, "角色切换失败")
    token = create_access_token(data={"sub": user.username, "user_id": user.id})
    set_token_cookie(response, token)
    return {"message": f"已切换为 {role_name}", "user": UserOut.from_orm(user)}

@router.get("/csrf-token")
async def get_csrf_token(csrf_protect: CsrfProtect = Depends()):
    csrf_token = csrf_protect.generate_csrf()
    return {"csrf_token": csrf_token}
