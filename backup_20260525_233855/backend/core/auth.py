from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.core.config import settings
from backend.core.database import get_db
from backend.models.user import User

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    try: return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)) -> User:
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id: raise HTTPException(401, "Invalid token")
    result = await db.execute(select(User).where(User.id == int(user_id)).options(selectinload(User.roles)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active: raise HTTPException(401, "User not found or inactive")
    return user

class RoleChecker:
    def __init__(self, allowed_roles: list[str]): self.allowed_roles = allowed_roles
    async def __call__(self, current_user: User = Depends(get_current_user)):
        if not any(role.name in self.allowed_roles for role in current_user.roles):
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return current_user
