"""Outbound email. Verification codes never belong in API responses."""

from app.services.email.backend import EmailMessage, get_email_backend, reset_email_backend

__all__ = ["EmailMessage", "get_email_backend", "reset_email_backend"]
