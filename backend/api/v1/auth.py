from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from backend.core.database import get_db
from backend.core.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, verify_token, get_current_user
)
from backend.core.blacklist import add_token_to_blacklist, is_token_blacklisted
from backend.models.user import User, create_user, get_user_by_username
from backend.schemas.user import UserCreate, UserOut, Token

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit("5/minute")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    exist = await get_user_by_username(db, user_data.username)
    if exist:
        raise HTTPException(status_code=400, detail="用户名已存在")
    if user_data.password != user_data.confirm_password:
        raise HTTPException(status_code=400, detail="两次密码不一致")
    user = await create_user(db, user_data.username, user_data.email, user_data.password)
    return user

@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    payload = verify_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="令牌类型错误")
    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        raise HTTPException(status_code=401, detail="刷新令牌已被使用")
    user_id = payload.get("sub")
    # 可选：验证用户存在
    user = await get_user_by_username(db, user_id)  # 可根据 id 查
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    # 将旧 refresh token 加入黑名单 (需要生成时带上 jti，这里简化)
    if jti:
        expire_in = payload.get("exp") - int(datetime.now(timezone.utc).timestamp())
        await add_token_to_blacklist(jti, max(expire_in, 0))
    new_access = create_access_token({"sub": user_id})
    new_refresh = create_refresh_token({"sub": user_id})
    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user