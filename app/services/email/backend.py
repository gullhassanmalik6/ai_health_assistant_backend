"""Email backend. SMTP in production; in-memory outbox in tests and local fallback."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeEmail
from typing import Protocol

from app.core.config import settings
from app.core.constants import VERIFICATION_CODE_TTL_SECONDS, VERIFICATION_EMAIL_SUBJECT
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailBackend(Protocol):
    async def send(self, message: EmailMessage) -> None: ...


@dataclass
class MemoryEmailBackend:
    outbox: list[EmailMessage] = field(default_factory=list)

    async def send(self, message: EmailMessage) -> None:
        self.outbox.append(message)
        logger.info("email_captured to=%s subject=%s", message.to, message.subject)


class SmtpEmailBackend:
    async def send(self, message: EmailMessage) -> None:
        mime = MimeEmail()
        mime["Subject"] = message.subject
        mime["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        mime["To"] = message.to
        mime.set_content(message.body)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(mime)


class LoggingEmailBackend:
    async def send(self, message: EmailMessage) -> None:
        logger.info("email_logged to=%s subject=%s\n%s", message.to, message.subject, message.body)


_backend: EmailBackend | None = None


def get_email_backend() -> EmailBackend:
    global _backend
    if _backend is not None:
        return _backend
    if settings.is_test:
        _backend = MemoryEmailBackend()
    elif settings.SMTP_HOST:
        _backend = SmtpEmailBackend()
    else:
        _backend = LoggingEmailBackend()
    return _backend


def reset_email_backend() -> None:
    global _backend
    _backend = None


def verification_email_body(code: str) -> str:
    minutes = VERIFICATION_CODE_TTL_SECONDS // 60
    return (
        f"Your AI Doctor verification code is {code}.\n\n"
        f"It expires in {minutes} minutes.\n\n"
        "If you did not create an account, you can ignore this email."
    )


async def send_verification_code(email: str, code: str) -> None:
    await get_email_backend().send(
        EmailMessage(
            to=email,
            subject=VERIFICATION_EMAIL_SUBJECT,
            body=verification_email_body(code),
        )
    )
