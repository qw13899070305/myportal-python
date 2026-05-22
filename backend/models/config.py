from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from backend.core.database import Base

class SiteConfig(Base):
    __tablename__ = "site_config"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
