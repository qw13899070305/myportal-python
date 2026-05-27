from sqlalchemy import Column, Integer, String, Boolean, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import Base

user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("role_id", Integer, ForeignKey("roles.id")),
)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    users = relationship("User", secondary=user_roles, back_populates="roles")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    roles = relationship("Role", secondary=user_roles, back_populates="users")

async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, username: str, email: str, password: str) -> User:
    from backend.core.security import get_password_hash
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user