"""文件相关请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from backend.core.filetypes import category_of


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    size: int = 0
    content_type: str | None = None
    uploader_id: int
    uploader: str | None = None
    upload_time: datetime | None = None
    deleted: bool = False
    #: 兼容旧前端字段名
    time: datetime | None = None

    @field_validator("uploader", mode="before")
    @classmethod
    def _uploader_name(cls, v):
        return getattr(v, "username", v)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def category(self) -> str:
        """文件分类键（``image`` / ``document`` / ``ebook`` …，规则见 core/filetypes.py）。

        按文件名实时派生：重命名后自动跟着变，也不会与历史数据对不上。
        这里只给机器键，中文标签由客户端自己翻译（网站用前端常量、APP 用自家资源）。
        """
        return category_of(self.name)


class FileListOut(BaseModel):
    total: int
    items: list[FileOut]


class FileRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def _clean(cls, v: str) -> str:
        # 只取基名，阻止通过重命名做路径穿越
        v = v.strip().replace("\\", "/").split("/")[-1].strip()
        if not v or v in {".", ".."}:
            raise ValueError("文件名不合法")
        return v


class TrashItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: int
    name: str
    size: int = 0
    deleted_time: datetime | None = None
    #: 兼容旧前端字段名
    time: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def category(self) -> str:
        """回收站条目同样带分类，规则与 :class:`FileOut` 一致。"""
        return category_of(self.name)


class TrashListOut(BaseModel):
    total: int
    items: list[TrashItemOut]
