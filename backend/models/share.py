"""文件分享链接模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.core.utils import utcnow
from backend.models.user import User


class ShareLink(Base):
    """一个分享码对应一个已上传的文件。

    ``file_path`` 存的是 :attr:`backend.models.file.FileItem.stored_name`
    （磁盘上的 UUID 文件名）。
    ``password`` 存的是 Argon2 哈希，不是明文。
    """

    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    #: 展示给用户的分享码
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    #: 访问密码的哈希（可空表示不需要密码）
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expire_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship("User", lazy="selectin")

    def is_expired(self, now: datetime | None = None) -> bool:
        return self.expire_at <= (now or utcnow())
