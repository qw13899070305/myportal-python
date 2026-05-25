
async def get_user_by_username(db: AsyncSession, username: str) -> User:
    from sqlalchemy import select
    from backend.models.user import User
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()
