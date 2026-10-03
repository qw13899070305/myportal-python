"""聊天与通知的请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    username: str = "未知"
    content: str
    is_recalled: bool = False
    created_at: datetime | None = None
    #: 兼容旧前端字段名
    time: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _from_orm_object(cls, data):
        """ORM 对象上没有 ``username``，需要从 ``user`` 关系里取。

        Pydantic 对缺失属性会直接套用默认值，字段级 validator 不会执行，
        所以这里用 ``mode="before"`` 显式构造。
        """
        message_user = getattr(data, "user", None)
        if message_user is None:
            return data
        created = getattr(data, "created_at", None)
        return {
            "id": data.id,
            "user_id": data.user_id,
            "username": getattr(message_user, "username", "未知"),
            "content": data.content,
            "is_recalled": data.is_recalled,
            "created_at": created,
            "time": str(created) if created else None,
        }


class ChatMessageListOut(BaseModel):
    total: int
    items: list[ChatMessageOut]


class ChatMessageIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

    @model_validator(mode="after")
    def _strip(self) -> "ChatMessageIn":
        self.content = self.content.strip()
        if not self.content:
            raise ValueError("消息不能为空")
        return self


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    content: str
    is_read: bool = False
    created_at: datetime | None = None
    from_user: str | None = None
    #: 兼容旧前端字段名
    time: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _from_orm_object(cls, data):
        sender = getattr(data, "from_user", None)
        if not hasattr(data, "type"):
            return data
        created = getattr(data, "created_at", None)
        return {
            "id": data.id,
            "type": data.type,
            "content": data.content,
            "is_read": data.is_read,
            "created_at": created,
            "time": str(created) if created else None,
            "from_user": getattr(sender, "username", None),
        }


class NotificationListOut(BaseModel):
    total: int
    unread: int
    items: list[NotificationOut]
