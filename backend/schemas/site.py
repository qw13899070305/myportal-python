"""站点配置与分享链接的请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.models.config import DEFAULT_SITE_CONFIG


class SiteConfigUpdate(BaseModel):
    """后台可修改的站点配置项。"""

    site_name: str | None = Field(default=None, max_length=100)
    announcement: str | None = Field(default=None, max_length=2000)
    allow_register: bool | None = None
    allow_upload: bool | None = None

    def to_pairs(self) -> list[tuple[str, str]]:
        """转换成 (key, value) 列表，只包含本次提交的字段。"""
        pairs: list[tuple[str, str]] = []
        for key in DEFAULT_SITE_CONFIG:
            value = getattr(self, key, None)
            if value is None:
                continue
            if isinstance(value, bool):
                pairs.append((key, "true" if value else "false"))
            else:
                pairs.append((key, str(value)))
        return pairs


class ShareCreate(BaseModel):
    """创建分享链接。"""

    #: 要分享的文件 ID
    file_id: int | None = None
    #: 兼容旧前端：直接给磁盘文件名
    filename: str | None = None
    password: str | None = Field(default=None, max_length=128)
    expire_hours: int | None = Field(default=None, ge=1, le=24 * 365)

    @field_validator("password")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class ShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    expire_at: datetime
    has_password: bool = False
    #: 兼容旧前端字段名
    password: str | None = None


class ShareAccessOut(BaseModel):
    filename: str
    download_url: str
