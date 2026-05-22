from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from backend.core.database import Base

class FileItem(Base):
    __tablename__ = "files"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    size: Mapped[int] = mapped_column(Integer)
    upload_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    uploader_id: Mapped[int] = mapped_column(Integer)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

class TrashItem(Base):
    __tablename__ = "trash"
    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(500))
    size: Mapped[int] = mapped_column(Integer)
    deleted_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
