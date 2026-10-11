"""Private profile photo upload and signed download URLs."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import PHOTO_ALLOWED_CONTENT_TYPES, PHOTO_MAX_BYTES
from app.core.exceptions import ValidationAppError
from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.repositories.user_repository import UserRepository
from app.services.profile_service import ProfileService
from app.services.storage.local import get_storage

_MAGIC = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/jpg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}

_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class PhotoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.profiles = ProfileRepository(session)
        self.storage = get_storage()

    def _validate_file(self, content_type: str | None, data: bytes) -> str:
        if not data:
            raise ValidationAppError(
                "Please check the highlighted fields.",
                details={"file": "Use a JPG, PNG or WebP image up to 5 MB"},
            )
        if len(data) > PHOTO_MAX_BYTES:
            raise ValidationAppError(
                "Please check the highlighted fields.",
                details={"file": "Use a JPG, PNG or WebP image up to 5 MB"},
            )
        normalized = (content_type or "").split(";")[0].strip().lower()
        if normalized not in PHOTO_ALLOWED_CONTENT_TYPES:
            raise ValidationAppError(
                "Please check the highlighted fields.",
                details={"file": "Use a JPG, PNG or WebP image up to 5 MB"},
            )
        prefixes = _MAGIC[normalized]
        if not any(data.startswith(prefix) for prefix in prefixes):
            if normalized == "image/webp" and b"WEBP" not in data[:16]:
                raise ValidationAppError(
                    "Please check the highlighted fields.",
                    details={"file": "Use a JPG, PNG or WebP image up to 5 MB"},
                )
            if normalized != "image/webp":
                raise ValidationAppError(
                    "Please check the highlighted fields.",
                    details={"file": "Use a JPG, PNG or WebP image up to 5 MB"},
                )
        return normalized

    async def upload(self, user: User, *, filename: str | None, content_type: str | None, data: bytes) -> User:
        media_type = self._validate_file(content_type, data)
        profile = await ProfileService(self.session).get_or_create_profile(user)
        if profile.profile_photo_key:
            await self.storage.delete(key=profile.profile_photo_key)
        key = f"profile-photos/{user.id}/{uuid.uuid4().hex}.{_EXTENSIONS[media_type]}"
        await self.storage.upload(key=key, data=data, content_type=media_type)
        profile.profile_photo_key = key
        profile.profile_photo_url = None
        await self.profiles.save(profile)
        loaded = await self.users.get_by_id(user.id)
        return loaded or user

    async def delete(self, user: User) -> User:
        profile = await ProfileService(self.session).get_or_create_profile(user)
        if profile.profile_photo_key:
            await self.storage.delete(key=profile.profile_photo_key)
        profile.profile_photo_key = None
        profile.profile_photo_url = None
        await self.profiles.save(profile)
        loaded = await self.users.get_by_id(user.id)
        return loaded or user

    async def signed_url(self, user: User) -> tuple[str | None, str | None]:
        profile = user.profile
        if not profile or not profile.profile_photo_key:
            return profile.profile_photo_url if profile else None, None
        url = await self.storage.generate_url(
            key=profile.profile_photo_key,
            expires_in=settings.PHOTO_SIGNED_URL_TTL_SECONDS,
        )
        from datetime import timedelta

        from app.core.security import utcnow

        expires = utcnow() + timedelta(seconds=settings.PHOTO_SIGNED_URL_TTL_SECONDS)
        return url, expires.isoformat().replace("+00:00", "Z")
