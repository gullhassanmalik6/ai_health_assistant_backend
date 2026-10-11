"""Email verification code flow."""

from app.core.constants import ErrorCode


def test_unverified_login_returns_403_and_does_not_leak_on_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "needverify@example.com", "password": "Sup3rSecret", "name": "Need Verify"},
    )
    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": "needverify@example.com", "password": "wrong-password"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["error_code"] == ErrorCode.AUTH_INVALID_CREDENTIALS

    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "needverify@example.com", "password": "Sup3rSecret"},
    )
    assert blocked.status_code == 403
    body = blocked.json()
    assert body["error_code"] == ErrorCode.AUTH_EMAIL_NOT_VERIFIED
    assert body["details"]["email"] == "needverify@example.com"
    assert "tokens" not in (body.get("data") or {})


def test_verify_email_success_and_already_verified(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "ok@example.com", "password": "Sup3rSecret", "name": "Ok"},
    )
    first = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "ok@example.com", "code": "123456"},
    )
    assert first.status_code == 200
    assert first.json()["data"]["verified"] is True
    again = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "ok@example.com", "code": "000000"},
    )
    assert again.status_code == 200
    assert again.json()["data"]["verified"] is True


def test_verify_email_wrong_code_and_unknown_email(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "code@example.com", "password": "Sup3rSecret", "name": "Code"},
    )
    wrong = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "code@example.com", "code": "000000"},
    )
    assert wrong.status_code == 400
    assert wrong.json()["error_code"] == ErrorCode.AUTH_CODE_INVALID
    assert "code" in wrong.json()["details"]

    unknown = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "nobody@example.com", "code": "123456"},
    )
    assert unknown.status_code == 400
    assert unknown.json()["error_code"] == ErrorCode.AUTH_CODE_INVALID


def test_verify_email_locks_after_five_wrong_attempts(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "lock@example.com", "password": "Sup3rSecret", "name": "Lock"},
    )
    for _ in range(4):
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"email": "lock@example.com", "code": "000000"},
        )
        assert response.status_code == 400
        assert response.json()["error_code"] == ErrorCode.AUTH_CODE_INVALID

    fifth = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "lock@example.com", "code": "000000"},
    )
    assert fifth.status_code == 429
    assert fifth.json()["error_code"] == ErrorCode.AUTH_CODE_ATTEMPTS_EXCEEDED


def test_session_blocks_unverified_email_account(client, tokens):
    from tests.helpers import auth_header, provision

    provision(
        client,
        tokens,
        "unverified-session",
        uid="fb-unverified-session",
        email="unverified-session@example.com",
        email_verified=False,
    )
    response = client.get("/api/v1/auth/session", headers=auth_header("unverified-session"))
    assert response.status_code == 403
    assert response.json()["error_code"] == ErrorCode.AUTH_EMAIL_NOT_VERIFIED


def test_resend_is_generic_and_rate_limited(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "resend@example.com", "password": "Sup3rSecret", "name": "Resend"},
    )
    unknown = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "missing@example.com"},
    )
    assert unknown.status_code == 200
    assert unknown.json()["data"]["resend_available_in"] == 60

    limited = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "resend@example.com"},
    )
    assert limited.status_code == 429
    assert limited.json()["error_code"] == ErrorCode.RATE_LIMITED
    assert "resend_available_in" in limited.json()["details"]
