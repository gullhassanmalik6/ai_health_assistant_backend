"""Shared test fixtures. Uses an in-memory SQLite database, never production."""

from __future__ import annotations

import os

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["CORS_ALLOWED_ORIGINS"] = "http://test"
os.environ["ALLOWED_HOSTS"] = "*"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_API_KEY"] = "test-api-key"
os.environ["FIREBASE_CLIENT_EMAIL"] = "test@test.iam.gserviceaccount.com"
os.environ["FIREBASE_PRIVATE_KEY"] = "-----BEGIN PRIVATE KEY-----\\nTEST\\n-----END PRIVATE KEY-----\\n"
os.environ["LOG_LEVEL"] = "WARNING"

import pytest
from fastapi.testclient import TestClient

from app.core.constants import AuthProvider, ErrorCode
from app.core.exceptions import AuthenticationError
from app.core.firebase import FirebaseSession
from app.main import app
from tests.helpers import TokenDirectory, auth_header, provision

__all__ = ["auth_header", "provision"]


@pytest.fixture
def tokens() -> TokenDirectory:
    return TokenDirectory()


@pytest.fixture
def firebase_mocks(monkeypatch, tokens: TokenDirectory):
    deleted: list[str] = []

    def fake_verify(token: str, *, check_revoked: bool = True):
        return tokens.verify(token, check_revoked=check_revoked)

    async def fake_signup(email: str, password: str, display_name: str | None = None) -> FirebaseSession:
        uid = f"fb-{email}"
        tokens.register("register-id-token", uid=uid, email=email, name=display_name)
        return FirebaseSession(
            uid=uid,
            email=email,
            id_token="register-id-token",
            refresh_token="register-refresh",
            expires_in=3600,
            email_verified=False,
            is_anonymous=False,
            display_name=display_name,
        )

    async def fake_signin(email: str, password: str) -> FirebaseSession:
        if password == "wrong-password":
            raise AuthenticationError(
                "Invalid email or password.",
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
            )
        uid = f"fb-{email}"
        tokens.register("login-id-token", uid=uid, email=email, email_verified=True)
        return FirebaseSession(
            uid=uid,
            email=email,
            id_token="login-id-token",
            refresh_token="login-refresh",
            expires_in=3600,
            email_verified=True,
            is_anonymous=False,
            display_name="Test User",
        )

    async def fake_anonymous() -> FirebaseSession:
        tokens.register(
            "guest-id-token",
            uid="fb-guest-1",
            email=None,
            name=None,
            provider=AuthProvider.ANONYMOUS,
            email_verified=False,
        )
        return FirebaseSession(
            uid="fb-guest-1",
            email=None,
            id_token="guest-id-token",
            refresh_token="guest-refresh",
            expires_in=3600,
            email_verified=False,
            is_anonymous=True,
        )

    async def fake_reset(email: str) -> None:
        return None

    async def fake_confirm(oob_code: str, new_password: str) -> None:
        if oob_code == "bad-code":
            raise AuthenticationError(
                "This password reset link is invalid or has expired.",
                error_code=ErrorCode.AUTH_TOKEN_INVALID,
            )

    async def fake_send_verification(id_token: str) -> None:
        return None

    async def fake_refresh(refresh_token: str) -> FirebaseSession:
        return FirebaseSession(
            uid="fb-refresh",
            email="user@example.com",
            id_token="refreshed-id-token",
            refresh_token=refresh_token,
            expires_in=3600,
            email_verified=True,
            is_anonymous=False,
        )

    def fake_delete(uid: str) -> None:
        deleted.append(uid)

    monkeypatch.setattr("app.dependencies.auth.verify_id_token", fake_verify)
    monkeypatch.setattr("app.core.firebase.verify_id_token", fake_verify)
    monkeypatch.setattr("app.core.firebase.sign_up_with_email", fake_signup)
    monkeypatch.setattr("app.core.firebase.sign_in_with_email", fake_signin)
    monkeypatch.setattr("app.core.firebase.sign_in_anonymously", fake_anonymous)
    monkeypatch.setattr("app.core.firebase.send_password_reset_email", fake_reset)
    monkeypatch.setattr("app.core.firebase.confirm_password_reset", fake_confirm)
    monkeypatch.setattr("app.core.firebase.send_email_verification", fake_send_verification)
    monkeypatch.setattr("app.core.firebase.refresh_id_token", fake_refresh)
    monkeypatch.setattr("app.core.firebase.delete_firebase_user", fake_delete)

    return {"deleted": deleted, "tokens": tokens}


@pytest.fixture
def client(firebase_mocks) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
