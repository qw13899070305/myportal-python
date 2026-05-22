from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Table, Column, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.database import Base
from argon2 import PasswordHasher

ph = PasswordHasher()

user_roles = Table("user_roles", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    roles: Mapped[list[Role]] = relationship(secondary=user_roles, back_populates="users", lazy="selectin")

    def set_password(self, password: str): self.hashed_password = ph.hash(password)
    def verify_password(self, password: str) -> bool:
        try: return ph.verify(self.hashed_password, password)
        except: return False
    def has_role(self, role_name: str) -> bool:
        return any(role.name == role_name for role in self.roles)
