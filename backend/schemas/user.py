import re
from pydantic import BaseModel, EmailStr, Field, validator


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    email: EmailStr | None = None

    @validator("password")
    def validate_password_strength(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("密码必须包含至少一个大写字母")
        if not re.search(r"[a-z]", v):
            raise ValueError("密码必须包含至少一个小写字母")
        if not re.search(r"[0-9]", v):
            raise ValueError("密码必须包含至少一个数字")
        # 可选：特殊字符
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("密码必须包含至少一个特殊字符")
        return v


class UserOut(BaseModel):
    id: int
    username: str
    email: str | None
    is_active: bool
    is_superuser: bool = False

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"