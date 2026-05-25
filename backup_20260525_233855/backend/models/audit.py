from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.database import Base
from backend.models.user import User

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user: Mapped[User | None] = relationship("User", lazy="selectin")
