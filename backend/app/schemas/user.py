"""Pydantic 请求/响应模型。"""
import re

from pydantic import BaseModel, Field, field_validator

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\u4e00-\u9fa5]{2,32}$")


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=6, max_length=64)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_PATTERN.match(v):
            raise ValueError("用户名仅支持 2-32 位中文、字母、数字、下划线")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=64)


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user) -> "UserOut":
        return cls(
            id=user.id,
            username=user.username,
            role=user.role,
            created_at=user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "",
        )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class MessageResponse(BaseModel):
    message: str
