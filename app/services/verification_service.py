"""6-digit email verification codes. Hashes only; never return the code."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    VERIFICATION_CODE_TTL_SECONDS,
    VERIFICATION_MAX_ATTEMPTS,
    VERIFICATION_RESEND_COOLDOWN_SECONDS,
    AuthProvider,
    ErrorCode,
)
from app.core.exceptions import AuthorizationError, BadRequestError, RateLimitError
from app.core.security import as_utc, utcnow
from app.models.user import User
from app.models.verification import EmailVerificationCode
from app.repositories.user_repository import UserRepository
from app.repositories.verification_repository import VerificationCodeRepository
from app.services.email.backend import send_verification_code
from app.utils.codes import codes_match, generate_verification_code, hash_verification_code


def seconds_until_resend(sent_at) -> int:
    elapsed = (utcnow() - as_utc(sent_at)).total_seconds()
    remaining = VERIFICATION_RESEND_COOLDOWN_SECONDS - int(elapsed)
    return max(0, remaining)


class VerificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.codes = VerificationCodeRepository(session)

    async def send_code(
        self,
        user: User,
        *,
        force: bool = False,
    ) -> tuple[bool, int]:
        """Send a new code. Returns (sent, resend_available_in)."""
        if not user.email or user.email_verified:
            return False, VERIFICATION_RESEND_COOLDOWN_SECONDS

        active = await self.codes.get_active_for_user(user.id)
        if active and not force:
            remaining = seconds_until_resend(active.sent_at)
            if remaining > 0:
                return False, remaining

        await self.codes.consume_all_for_user(user.id)
        code = generate_verification_code()
        now = utcnow()
        await self.codes.create(
            EmailVerificationCode(
                user_id=user.id,
                email=user.email,
                code_hash=hash_verification_code(code, user.email),
                expires_at=now + timedelta(seconds=VERIFICATION_CODE_TTL_SECONDS),
                attempt_count=0,
                sent_at=now,
            )
        )
        await send_verification_code(user.email, code)
        return True, VERIFICATION_RESEND_COOLDOWN_SECONDS

    async def send_for_login(self, user: User) -> tuple[bool, int]:
        return await self.send_code(user, force=False)

    async def resend(self, email: str) -> dict[str, int]:
        normalized = email.strip().lower()
        user = await self.users.get_by_email(normalized)
        if user is None or user.email_verified or user.auth_provider != AuthProvider.EMAIL.value:
            return {"resend_available_in": VERIFICATION_RESEND_COOLDOWN_SECONDS}

        active = await self.codes.get_active_for_user(user.id)
        if active:
            remaining = seconds_until_resend(active.sent_at)
            if remaining > 0:
                raise RateLimitError(
                    "Please wait before requesting another code.",
                    details={"resend_available_in": remaining},
                )

        await self.send_code(user, force=True)
        return {"resend_available_in": VERIFICATION_RESEND_COOLDOWN_SECONDS}

    async def verify(self, email: str, code: str) -> dict[str, bool]:
        from app.core import firebase as firebase_auth

        normalized = email.strip().lower()
        user = await self.users.get_by_email(normalized)
        if user is None:
            raise BadRequestError(
                "That code isn't right. Check the email and try again.",
                error_code=ErrorCode.AUTH_CODE_INVALID,
                details={"code": "That code isn't right. Check the email and try again."},
            )
        if user.email_verified:
            return {"verified": True}

        active = await self.codes.get_active_for_user(user.id)
        if active is None:
            raise BadRequestError(
                "That code isn't right. Check the email and try again.",
                error_code=ErrorCode.AUTH_CODE_INVALID,
                details={"code": "That code isn't right. Check the email and try again."},
            )

        now = utcnow()
        if as_utc(active.expires_at) <= now:
            active.consumed_at = now
            await self.codes.save(active)
            await self.session.commit()
            raise BadRequestError(
                "This code has expired. Resend the code to get a new one.",
                error_code=ErrorCode.AUTH_CODE_EXPIRED,
                details={"code": "This code has expired. Resend the code to get a new one."},
            )

        if not codes_match(code, normalized, active.code_hash):
            active.attempt_count += 1
            if active.attempt_count >= VERIFICATION_MAX_ATTEMPTS:
                active.consumed_at = now
                await self.codes.save(active)
                await self.session.commit()
                raise RateLimitError(
                    "Too many attempts. Resend the code to get a new one.",
                    error_code=ErrorCode.AUTH_CODE_ATTEMPTS_EXCEEDED,
                    details={"code": "Too many attempts. Resend the code to get a new one."},
                )
            await self.codes.save(active)
            await self.session.commit()
            raise BadRequestError(
                "That code isn't right. Check the email and try again.",
                error_code=ErrorCode.AUTH_CODE_INVALID,
                details={"code": "That code isn't right. Check the email and try again."},
            )

        user.email_verified = True
        await self.users.save(user)
        active.consumed_at = now
        await self.codes.save(active)
        firebase_auth.set_firebase_email_verified(user.firebase_uid, True)
        return {"verified": True}


def require_verified_email_session(user: User) -> None:
    if user.auth_provider == AuthProvider.EMAIL.value and not user.email_verified:
        raise AuthorizationError(
            "Verify your email to log in.",
            error_code=ErrorCode.AUTH_EMAIL_NOT_VERIFIED,
            details={"email": user.email, "code_sent": False, "resend_available_in": 0},
        )
