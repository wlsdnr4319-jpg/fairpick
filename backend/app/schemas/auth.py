from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)  # 8자 이상 (레퍼런스 10장)
    nickname: str = Field(min_length=1, max_length=30)
    # 만 14세 미만은 법정대리인 동의가 필요해 가입을 받지 않는다 (레퍼런스 15장)
    is_over_14: bool

    @field_validator("nickname")
    @classmethod
    def strip_nickname(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("닉네임을 입력해 주세요")
        return v

    @field_validator("is_over_14")
    @classmethod
    def must_be_over_14(cls, v: bool) -> bool:
        if not v:
            raise ValueError("만 14세 이상만 가입할 수 있어요")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str | None  # 소셜 로그인으로 가입하고 이메일 제공에 동의하지 않으면 없다
    nickname: str
    role: Literal["user", "admin"]


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # 초
    user: UserOut


class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetConfirmIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)


class NotificationSettingsIO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email_enabled: bool
    prereg_deadline: bool
    opening_soon: bool
    fair_updated: bool


class UnsubscribeIn(BaseModel):
    token: str = Field(min_length=10, max_length=64)


class MessageOut(BaseModel):
    message: str


class BookmarkOut(BaseModel):
    fair_id: int
    bookmarked: bool
    bookmark_count: int
