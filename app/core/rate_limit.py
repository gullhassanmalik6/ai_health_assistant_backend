"""In-memory rate limiter. Redis can replace the storage backend later."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def _key_func(request) -> str:
    return get_remote_address(request)


limiter = Limiter(
    key_func=_key_func,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    enabled=settings.RATE_LIMIT_ENABLED and not settings.is_test,
    headers_enabled=True,
)


def auth_limit() -> str:
    return f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute"
