"""通用响应模型。"""

from pydantic import BaseModel


class Message(BaseModel):
    """简单文本响应。"""

    message: str


class Ok(BaseModel):
    """简单成功响应。"""

    ok: bool = True
