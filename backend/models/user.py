from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from argon2 import PasswordHasher
from backend.core.database import Base
from backend.core.config import settings
import datetime

ph = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
)

user_roles = Table(
    'user_roles', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100))
    hashed_password = Column(String(255), nullable=False)
    avatar = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    roles = relationship("Role", secondary=user_roles, back_populates="users")

    def set_password(self, password: str):
        self.hashed_password = ph.hash(password)

    def verify_password(self, password: str) -> bool:
        try:
            return ph.verify(self.hashed_password, password)
        except Exception:
            return False

    def has_role(self, role_name: str) -> bool:
        return any(role.name == role_name for role in self.roles)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    users = relationship("User", secondary=user_roles, back_populates="roles")
