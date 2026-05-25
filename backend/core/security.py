from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from datetime import datetime, timedelta
from backend.core.config import settings
from backend.core.database import get_db
from backend.models.user import User

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    payload = verify_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="令牌无效")
    from backend.services.user_service import get_user_by_username
    user = await get_user_by_username(db, username)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user
