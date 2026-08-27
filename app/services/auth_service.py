"""Authentication and identity provisioning. Passwords never touch PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import firebase as firebase_auth
from app.core.constants import (
    GENERIC_PASSWORD_RESET_MESSAGE,
    AuthProvider,
    ErrorCode,
)
from app.core.exceptions import AuthenticationError, AuthorizationError, FirebaseServiceError
from app.core.firebase import FirebaseSession, FirebaseTokenClaims
from app.core.logging import get_logger
from app.core.security import as_utc, auth_time_to_datetime, utcnow
from app.models.user import User
from app.models.user_profile import UserProfile
from app.repositories.profile_repository import ProfileRepository
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


@dataclass(slots=True)
class AuthResult:
    user: User
    session: FirebaseSession | None
    claims: FirebaseTokenClaims | None = None


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.profiles = ProfileRepository(session)

    async def register(self, *, email: str, password: str, name: str) -> AuthResult:
        normalized_email = email.strip().lower()
        firebase_session: FirebaseSession | None = None
        try:
            firebase_session = await firebase_auth.sign_up_with_email(
                normalized_email, password, display_name=name.strip()
            )
            user = await self._create_application_user(
                firebase_uid=firebase_session.uid,
                email=normalized_email,
                name=name.strip(),
                provider=AuthProvider.EMAIL,
                is_guest=False,
                email_verified=firebase_session.email_verified,
            )
            return AuthResult(user=user, session=firebase_session)
        except Exception:
            if firebase_session and firebase_session.uid:
                try:
                    firebase_auth.delete_firebase_user(firebase_session.uid)
                except FirebaseServiceError:
                    logger.error("Failed to roll back Firebase identity after registration error.")
            raise

    async def login(self, *, email: str, password: str) -> AuthResult:
        firebase_session = await firebase_auth.sign_in_with_email(email.strip().lower(), password)
        claims = firebase_auth.verify_id_token(firebase_session.id_token, check_revoked=False)
        user = await self.upsert_from_claims(
            claims,
            name=firebase_session.display_name,
            mark_login=True,
        )
        return AuthResult(user=user, session=firebase_session, claims=claims)

    async def authenticate_with_id_token(
        self,
        id_token: str,
        *,
        expected_provider: AuthProvider | None = None,
    ) -> AuthResult:
        claims = firebase_auth.verify_id_token(id_token)
        if expected_provider and claims.provider != expected_provider:
            raise AuthenticationError(
                "Authentication provider does not match this endpoint.",
                error_code=ErrorCode.AUTH_PROVIDER_MISMATCH,
            )
        user = await self.upsert_from_claims(claims, name=claims.name, mark_login=True)
        session = FirebaseSession(
            uid=claims.uid,
            email=claims.email,
            id_token=id_token,
            refresh_token=None,
            expires_in=3600,
            email_verified=claims.email_verified,
            is_anonymous=claims.provider == AuthProvider.ANONYMOUS,
            display_name=claims.name,
        )
        return AuthResult(user=user, session=session, claims=claims)

    async def start_guest_session(self) -> AuthResult:
        firebase_session = await firebase_auth.sign_in_anonymously()
        claims = firebase_auth.verify_id_token(firebase_session.id_token, check_revoked=False)
        user = await self.upsert_from_claims(claims, mark_login=True)
        return AuthResult(user=user, session=firebase_session, claims=claims)

    async def logout(self, user: User) -> None:
        user.token_invalidated_at = utcnow()
        await self.users.save(user)

    async def forgot_password(self, email: str) -> str:
        await firebase_auth.send_password_reset_email(email.strip().lower())
        return GENERIC_PASSWORD_RESET_MESSAGE

    async def reset_password(self, *, oob_code: str, new_password: str) -> None:
        await firebase_auth.confirm_password_reset(oob_code, new_password)

    async def send_verification(self, id_token: str) -> None:
        await firebase_auth.send_email_verification(id_token)

    async def refresh(self, refresh_token: str) -> AuthResult:
        firebase_session = await firebase_auth.refresh_id_token(refresh_token)
        claims = firebase_auth.verify_id_token(firebase_session.id_token, check_revoked=False)
        user = await self.upsert_from_claims(claims, mark_login=False)
        return AuthResult(user=user, session=firebase_session, claims=claims)

    async def verification_status(self, user: User, claims: FirebaseTokenClaims) -> bool:
        verified = bool(claims.email_verified)
        if user.email_verified != verified:
            user.email_verified = verified
            await self.users.save(user)
        return verified

    async def upsert_from_claims(
        self,
        claims: FirebaseTokenClaims,
        *,
        name: str | None = None,
        mark_login: bool = False,
    ) -> User:
        user = await self.users.get_by_firebase_uid(claims.uid)
        is_guest = claims.provider == AuthProvider.ANONYMOUS
        email = claims.email.lower() if claims.email else None

        if user is None:
            user = await self._create_application_user(
                firebase_uid=claims.uid,
                email=email,
                name=(name or claims.name),
                provider=claims.provider,
                is_guest=is_guest,
                email_verified=claims.email_verified,
            )
        else:
            if not user.is_active:
                raise AuthorizationError(
                    "This account has been disabled.",
                    error_code=ErrorCode.AUTH_ACCOUNT_DISABLED,
                )
            user.email = email or user.email
            if name and not user.name:
                user.name = name
            elif claims.name and not user.name:
                user.name = claims.name
            user.email_verified = claims.email_verified
            user.auth_provider = claims.provider.value
            # Linking an email/social credential to an anonymous identity upgrades the guest.
            if user.is_guest and not is_guest:
                user.is_guest = False
            if mark_login:
                user.last_login_at = utcnow()
            await self.users.save(user)

        if user.profile is None:
            existing = await self.profiles.get_by_user_id(user.id)
            if existing is None:
                await self.profiles.create(UserProfile(user_id=user.id))

        if mark_login and user.last_login_at is None:
            user.last_login_at = utcnow()
            await self.users.save(user)

        loaded = await self.users.get_by_id(user.id)
        return loaded or user

    async def assert_session_active(self, user: User, claims: FirebaseTokenClaims) -> None:
        if not user.is_active:
            raise AuthorizationError(
                "This account has been disabled.",
                error_code=ErrorCode.AUTH_ACCOUNT_DISABLED,
            )
        if user.token_invalidated_at and claims.auth_time is not None:
            issued = auth_time_to_datetime(claims.auth_time)
            if issued is not None and issued < as_utc(user.token_invalidated_at):
                raise AuthenticationError(
                    "Session is no longer valid. Please sign in again.",
                    error_code=ErrorCode.AUTH_SESSION_REVOKED,
                )

    async def _create_application_user(
        self,
        *,
        firebase_uid: str,
        email: str | None,
        name: str | None,
        provider: AuthProvider,
        is_guest: bool,
        email_verified: bool,
    ) -> User:
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            name=name,
            auth_provider=provider.value,
            is_guest=is_guest,
            is_active=True,
            email_verified=email_verified,
            onboarding_completed=False,
            last_login_at=utcnow(),
        )
        user = await self.users.create(user)
        await self.profiles.create(UserProfile(user_id=user.id))
        loaded = await self.users.get_by_id(user.id)
        return loaded or user
