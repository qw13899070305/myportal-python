from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.user import User
import logging

logger = logging.getLogger(__name__)


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    try:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"查询用户失败: {e}")
        return None


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"查询用户失败: {e}")
        return None


async def create_user(db: AsyncSession, username: str, password: str, email: str = None) -> User:
    existing = await get_user_by_username(db, username)
    if existing:
        raise ValueError("用户名已存在")
    user = User(username=username, email=email, is_active=True)
    user.set_password(password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not user.check_password(password):
        return None
    return user


async def update_user_password(db: AsyncSession, user_id: int, new_password: str) -> bool:
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    user.set_password(new_password)
    await db.commit()
    return True