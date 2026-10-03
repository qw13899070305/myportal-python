"""用户相关请求/响应模型（Pydantic v2）。"""

import re
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

_SPECIAL_CHARS = re.compile(r"[!@#$%^&*(),.?\":{}|<>_\-+=/\\\[\]~`';]")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fa5.-]+$")


def validate_password_strength(value: str) -> str:
    """密码强度：至少一个大写、一个小写、一个数字、一个特殊字符。"""
    checks = (
        (r"[A-Z]", "密码必须包含至少一个大写字母"),
        (r"[a-z]", "密码必须包含至少一个小写字母"),
        (r"[0-9]", "密码必须包含至少一个数字"),
    )
    for pattern, message in checks:
        if not re.search(pattern, value):
            raise ValueError(message)
    if not _SPECIAL_CHARS.search(value):
        raise ValueError("密码必须包含至少一个特殊字符")
    return value


def _clean_username(v: str) -> str:
    v = v.strip()
    if not _USERNAME_RE.match(v):
        raise ValueError("用户名只能包含中英文、数字、下划线、点或连字符")
    return v


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    # 前端会一起提交；缺省时跳过一致性校验
    confirm_password: str | None = Field(default=None, max_length=128)
    email: EmailStr | None = None

    @field_validator("username")
    @classmethod
    def _check_username(cls, v: str) -> str:
        return _clean_username(v)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def _passwords_match(self) -> "UserCreate":
        if self.confirm_password is not None and self.confirm_password != self.password:
            raise ValueError("两次输入的密码不一致")
        return self


class UserApply(BaseModel):
    """注册申请（``POST /users/apply``，兼容旧前端）。

    ``requested_role`` 只接受普通角色，管理类角色一律忽略，
    避免客户端自行提权。
    """

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    email: EmailStr | None = None
    requested_role: str | None = Field(default=None, max_length=50)

    @field_validator("username")
    @classmethod
    def _check_username(cls, v: str) -> str:
        return _clean_username(v)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _check_new_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None
    is_active: bool = True
    roles: list[str] = Field(default_factory=list)
    avatar_url: str | None = None

    @field_validator("roles", mode="before")
    @classmethod
    def _flatten_roles(cls, v):
        """把 ORM 的 Role 对象列表转换为角色名列表。"""
        if not v:
            return []
        return [getattr(role, "name", role) for role in v]


class UserListOut(BaseModel):
    total: int
    items: list[UserOut]


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LoginRequest(BaseModel):
    """JSON 方式登录（``POST /auth/login`` 同时支持表单与 JSON）。"""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)
    captcha_id: str | None = None
    captcha_code: str | None = None


class AvatarOut(BaseModel):
    avatar_url: str


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    action: str
    detail: str | None = None
    ip_address: str = ""
    created_at: datetime | None = None
