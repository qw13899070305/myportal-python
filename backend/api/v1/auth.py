import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database import get_db
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user,
    add_token_to_blacklist,
    is_token_blacklisted,
    oauth2_scheme,
)
from backend.services.user_service import authenticate_user, create_user, get_user_by_id
from backend.schemas.user import UserCreate, UserOut, Token
from backend.models.user import User
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user = await create_user(db, user_data.username, user_data.password, user_data.email)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")

    jti = str(uuid.uuid4())
    access_token = create_access_token(data={"sub": user.id, "jti": jti})
    refresh_token = create_refresh_token(data={"sub": user.id, "jti": jti})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    payload = verify_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌")

    jti = payload.get("jti")
    if await is_token_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌已失效")

    user_id = payload.get("sub")
    user = await get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    # 将旧 refresh token 加入黑名单（一次性使用）
    expire_time = payload.get("exp")
    if expire_time:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).timestamp()
        ttl = int(expire_time - now)
        if ttl > 0:
            await add_token_to_blacklist(jti, ttl)

    new_jti = str(uuid.uuid4())
    new_access = create_access_token(data={"sub": user.id, "jti": new_jti})
    new_refresh = create_refresh_token(data={"sub": user.id, "jti": new_jti})
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    access_token: str = Depends(oauth2_scheme),
    refresh_token: str = None
):
    # 拉黑 access token
    access_payload = verify_token(access_token)
    access_jti = access_payload.get("jti")
    access_exp = access_payload.get("exp")
    if access_exp:
        from datetime import datetime, timezone
        ttl = int(access_exp - datetime.now(timezone.utc).timestamp())
        if ttl > 0:
            await add_token_to_blacklist(access_jti, ttl)

    # 拉黑 refresh token（如果提供）
    if refresh_token:
        refresh_payload = verify_token(refresh_token)
        refresh_jti = refresh_payload.get("jti")
        refresh_exp = refresh_payload.get("exp")
        if refresh_exp:
            from datetime import datetime, timezone
            ttl = int(refresh_exp - datetime.now(timezone.utc).timestamp())
            if ttl > 0:
                await add_token_to_blacklist(refresh_jti, ttl)

    return {"detail": "已退出登录"}


@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user