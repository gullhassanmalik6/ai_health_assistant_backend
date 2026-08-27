"""Shared test helpers. TokenDirectory is defined here so tests need not import conftest."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.core.constants import AuthProvider, ErrorCode
from app.core.exceptions import AuthenticationError
from app.core.firebase import FirebaseTokenClaims


class TokenDirectory:
    def __init__(self) -> None:
        self.claims: dict[str, FirebaseTokenClaims] = {}

    def register(
        self,
        token: str,
        *,
        uid: str,
        email: str | None = "user@example.com",
        name: str | None = "Test User",
        provider: AuthProvider = AuthProvider.EMAIL,
        email_verified: bool = True,
        auth_time: int | None = None,
    ) -> str:
        self.claims[token] = FirebaseTokenClaims(
            uid=uid,
            email=email,
            name=name,
            email_verified=email_verified,
            provider=provider,
            auth_time=auth_time or int(time.time()),
            raw={"uid": uid},
        )
        return token

    def verify(self, token: str, *, check_revoked: bool = True) -> FirebaseTokenClaims:
        if token == "expired-token":
            raise AuthenticationError(
                "Authentication token has expired.",
                error_code=ErrorCode.AUTH_TOKEN_EXPIRED,
            )
        if token == "invalid-token" or token not in self.claims:
            raise AuthenticationError(
                "Invalid authentication token.",
                error_code=ErrorCode.AUTH_TOKEN_INVALID,
            )
        return self.claims[token]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def provision(client: TestClient, tokens: TokenDirectory, token: str, **kwargs) -> dict:
    tokens.register(token, **kwargs)
    response = client.get("/api/v1/users/me", headers=auth_header(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    return body["data"]
