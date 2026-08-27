"""Current-user schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import MAX_NAME_LENGTH


class UserMeData(BaseModel):
    id: str
    firebase_uid: str
    email: str | None
    name: str | None
    auth_provider: str
    is_guest: bool
    is_active: bool
    email_verified: bool
    onboarding_completed: bool
    profile_completed: bool
    profile_completion_percentage: int
    created_at: datetime
    last_login_at: datetime | None = None


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    onboarding_completed: bool | None = None
