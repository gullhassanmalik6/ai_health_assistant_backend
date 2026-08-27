"""Authentication request and response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import MAX_NAME_LENGTH, MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty.")
        return cleaned

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class SocialAuthRequest(BaseModel):
    id_token: str = Field(min_length=10, description="Firebase ID token issued after Google/Apple sign-in.")


class GuestAuthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class ResetPasswordRequest(BaseModel):
    oob_code: str = Field(min_length=1, description="Firebase password-reset action code from the email link.")
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class TokenPayload(BaseModel):
    id_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    token_type: str = "Bearer"


class AuthUserPayload(BaseModel):
    id: str
    firebase_uid: str
    email: str | None
    name: str | None
    auth_provider: str
    is_guest: bool
    email_verified: bool
    onboarding_completed: bool
    profile_completion_percentage: int
    profile_completed: bool
    created_at: datetime
    last_login_at: datetime | None = None


class AuthData(BaseModel):
    user: AuthUserPayload
    tokens: TokenPayload | None = None
    is_guest: bool
    email_verified: bool
    profile_completed: bool


class VerificationStatusData(BaseModel):
    verified: bool
