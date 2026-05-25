from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from argon2 import PasswordHasher
from backend.core.database import Base
import datetime

# ✅ 显式设置 argon2 参数
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100))
    hashed_password = Column(String(255), nullable=False)
    avatar = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    roles = relationship("Role", secondary="user_roles", back_populates="users")

    def set_password(self, password: str):
        self.hashed_password = ph.hash(password)

    def verify_password(self, password: str) -> bool:
        try:
            return ph.verify(self.hashed_password, password)
        except:
            return False

    def has_role(self, role_name: str) -> bool:
        return any(role.name == role_name for role in self.roles)
