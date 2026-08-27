"""Authentication and authorization dependencies.

Identity is always derived from a verified Firebase ID token.
Client-supplied user IDs are never trusted.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ErrorCode
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.firebase import FirebaseTokenClaims, verify_id_token
from app.models.user import User
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class AuthenticatedContext:
    user: User
    claims: FirebaseTokenClaims
    raw_token: str


async def get_token_credentials(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> HTTPAuthorizationCredentials:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise AuthenticationError(
            "Missing authentication token.",
            error_code=ErrorCode.AUTH_TOKEN_MISSING,
        )
    return credentials


async def get_current_context(
    credentials: HTTPAuthorizationCredentials = Depends(get_token_credentials),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedContext:
    claims = verify_id_token(credentials.credentials)
    service = AuthService(db)
    user = await service.upsert_from_claims(claims, name=claims.name, mark_login=False)
    await service.assert_session_active(user, claims)
    return AuthenticatedContext(user=user, claims=claims, raw_token=credentials.credentials)


async def get_current_user(
    context: AuthenticatedContext = Depends(get_current_context),
) -> User:
    """Any valid Firebase identity, including guests."""
    return context.user


async def get_authenticated_user(
    user: User = Depends(get_current_user),
) -> User:
    """Registered (non-guest) user. Guests are rejected."""
    if user.is_guest:
        raise AuthorizationError(
            "This action requires a registered account.",
            error_code=ErrorCode.AUTH_GUEST_FORBIDDEN,
        )
    return user


async def require_registered_user(
    user: User = Depends(get_authenticated_user),
) -> User:
    return user
