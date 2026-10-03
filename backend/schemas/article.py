"""文章相关请求/响应模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_tags(tags) -> list[str]:
    """去空、去重、保持顺序，并限制数量与单个标签长度。"""
    result: list[str] = []
    for raw in tags or []:
        name = str(raw).strip()[:50]
        if name and name not in result:
            result.append(name)
    return result[:10]


class ArticleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    is_internal: bool = False
    #: 管理员可以直接指定状态；普通用户提交时会被忽略
    status: str | None = None

    @field_validator("title", "content")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("不能为空")
        return v

    @field_validator("tags")
    @classmethod
    def _tags(cls, v):
        return normalize_tags(v)


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None
    is_internal: bool | None = None
    is_pinned: bool | None = None
    status: str | None = None

    @field_validator("tags")
    @classmethod
    def _tags(cls, v):
        return None if v is None else normalize_tags(v)


class ArticleReview(BaseModel):
    action: Literal["approve", "reject"]


class ArticleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    summary: str = ""
    author: str = "未知"
    author_id: int
    status: str = "pending"
    is_pinned: bool = False
    is_internal: bool = False
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    likes_count: int = 0
    comments_count: int = 0
    is_liked: bool = False
    is_bookmarked: bool = False

    @field_validator("author", mode="before")
    @classmethod
    def _author_name(cls, v):
        return getattr(v, "username", v) or "未知"

    @field_validator("tags", mode="before")
    @classmethod
    def _tag_names(cls, v):
        if not v:
            return []
        return [getattr(tag, "name", tag) for tag in v]


class ArticleDetail(ArticleListItem):
    content: str = ""
    updated_at: datetime | None = None


class ArticleListOut(BaseModel):
    total: int
    items: list[ArticleListItem]


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: int | None = None

    @field_validator("content")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("评论内容不能为空")
        return v


class CommentUser(BaseModel):
    """评论作者（嵌套对象，前端用 ``c.user.username`` 读取）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    article_id: int
    user_id: int
    username: str = "用户"
    parent_id: int | None = None
    content: str
    created_at: datetime | None = None
    #: 同时提供嵌套形式，兼容 ``c.user?.username`` 的写法
    user: CommentUser | None = None

    @model_validator(mode="before")
    @classmethod
    def _from_orm_object(cls, data):
        """ORM 对象上没有 ``username`` 字段，需要从 ``user`` 关系里取。

        Pydantic 在属性缺失时会直接用默认值，字段级 validator 不会被调用，
        因此这里用 ``mode="before"`` 显式构造字典。
        """
        comment_user = getattr(data, "user", None)
        if comment_user is None:
            return data
        return {
            "id": data.id,
            "article_id": data.article_id,
            "user_id": data.user_id,
            "parent_id": data.parent_id,
            "content": data.content,
            "created_at": data.created_at,
            "username": getattr(comment_user, "username", "用户"),
            "user": comment_user,
        }


class CommentListOut(BaseModel):
    total: int
    items: list[CommentOut]


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("分类名不能为空")
        return v
