from pydantic import BaseModel, EmailStr, Field, validator
import re

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    email: EmailStr | None = None

    @validator("password")
    def validate_password(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("密码必须包含大写字母")
        if not re.search(r"[a-z]", v):
            raise ValueError("密码必须包含小写字母")
        if not re.search(r"[0-9]", v):
            raise ValueError("密码必须包含数字")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("密码必须包含特殊字符")
        return v

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("两次密码不一致")
        return v

class UserOut(BaseModel):
    id: int
    username: str
    email: str | None
    is_active: bool = True

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"