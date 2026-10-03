"""站点配置（键值对）。"""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base

#: 允许通过后台修改的配置项及其默认值
DEFAULT_SITE_CONFIG: dict[str, str] = {
    "site_name": "MyPortal",
    "announcement": "",
    "allow_register": "true",
    "allow_upload": "true",
}


class SiteConfig(Base):
    __tablename__ = "site_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, default="")
