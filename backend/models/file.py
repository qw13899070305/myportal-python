"""文件与回收站模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.core.utils import utcnow
from backend.models.user import User


class FileItem(Base):
    """已上传的文件。

    软删除设计：删除时把 ``deleted`` 置为 True 并在 ``trash`` 表里
    记录一条 :class:`TrashItem`，据此可以从回收站恢复或彻底删除。
    """

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    #: 展示给用户的原始文件名
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    #: 实际落盘的 UUID 文件名（磁盘上只用这个名字，从根本上避免路径穿越）
    stored_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    #: 用 BigInteger：单文件上限已提到 30GB，换成 32 位整数的库会溢出
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    upload_time: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    uploader: Mapped[User] = relationship("User", lazy="selectin")


class TrashItem(Base):
    """回收站条目：指向一个被软删除的 :class:`FileItem`。"""

    __tablename__ = "trash"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted_time: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    file: Mapped[FileItem] = relationship("FileItem", lazy="selectin")
