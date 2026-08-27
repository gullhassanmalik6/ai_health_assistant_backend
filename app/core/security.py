"""Security helpers that do not belong to a single router."""

from datetime import datetime, timezone

from app.core.constants import AuthProvider


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_guest_provider(provider: AuthProvider, is_guest_flag: bool) -> bool:
    return is_guest_flag or provider == AuthProvider.ANONYMOUS


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def auth_time_to_datetime(auth_time: int | None) -> datetime | None:
    if auth_time is None:
        return None
    return datetime.fromtimestamp(auth_time, tz=timezone.utc)
