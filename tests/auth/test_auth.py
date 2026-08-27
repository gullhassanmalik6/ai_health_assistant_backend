"""Authentication API tests."""

from app.core.constants import AuthProvider, ErrorCode
from tests.helpers import auth_header, provision


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_ready(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_register_creates_user_without_storing_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "Sup3rSecret", "name": "New User"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["user"]["email"] == "new@example.com"
    assert body["data"]["user"]["is_guest"] is False
    assert body["data"]["email_verified"] is False
    assert "password" not in body["data"]["user"]
    assert body["data"]["tokens"]["id_token"]


def test_login_success(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "Sup3rSecret", "name": "Login User"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "Sup3rSecret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["user"]["email"] == "login@example.com"


def test_login_invalid_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == ErrorCode.AUTH_INVALID_CREDENTIALS


def test_missing_token_rejected(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error_code"] == ErrorCode.AUTH_TOKEN_MISSING


def test_invalid_token_rejected(client):
    response = client.get("/api/v1/users/me", headers=auth_header("invalid-token"))
    assert response.status_code == 401
    assert response.json()["error_code"] == ErrorCode.AUTH_TOKEN_INVALID


def test_expired_token_rejected(client):
    response = client.get("/api/v1/users/me", headers=auth_header("expired-token"))
    assert response.status_code == 401
    assert response.json()["error_code"] == ErrorCode.AUTH_TOKEN_EXPIRED


def test_valid_token_returns_current_user(client, tokens):
    user = provision(client, tokens, "valid-token", uid="fb-valid", email="valid@example.com")
    assert user["email"] == "valid@example.com"
    assert user["is_guest"] is False
    assert user["firebase_uid"] == "fb-valid"


def test_guest_authentication(client):
    response = client.post("/api/v1/auth/guest")
    assert response.status_code == 201
    body = response.json()
    assert body["data"]["is_guest"] is True
    assert body["data"]["user"]["is_guest"] is True
    assert body["data"]["user"]["email"] is None


def test_registered_user_flag(client, tokens):
    user = provision(
        client,
        tokens,
        "reg-token",
        uid="fb-reg",
        email="reg@example.com",
        provider=AuthProvider.EMAIL,
    )
    assert user["is_guest"] is False
    assert user["auth_provider"] == "email"


def test_google_auth_derives_identity_from_token(client, tokens):
    tokens.register(
        "google-id-token-valid-xxxxxxxx",
        uid="fb-google",
        email="google@example.com",
        name="Google User",
        provider=AuthProvider.GOOGLE,
    )
    response = client.post(
        "/api/v1/auth/google",
        json={"id_token": "google-id-token-valid-xxxxxxxx"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["user"]["auth_provider"] == "google"
    assert body["data"]["user"]["email"] == "google@example.com"


def test_google_auth_rejects_mismatched_provider(client, tokens):
    tokens.register(
        "email-as-google-token-xxxx",
        uid="fb-mismatch",
        email="mismatch@example.com",
        provider=AuthProvider.EMAIL,
    )
    response = client.post(
        "/api/v1/auth/google",
        json={"id_token": "email-as-google-token-xxxx"},
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == ErrorCode.AUTH_PROVIDER_MISMATCH


def test_apple_auth(client, tokens):
    tokens.register(
        "apple-id-token-valid-xxxxxxxx",
        uid="fb-apple",
        email="apple@example.com",
        provider=AuthProvider.APPLE,
    )
    response = client.post(
        "/api/v1/auth/apple",
        json={"id_token": "apple-id-token-valid-xxxxxxxx"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["user"]["auth_provider"] == "apple"


def test_forgot_password_does_not_leak_existence(client):
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "unknown@example.com"},
    )
    assert response.status_code == 200
    assert "If the account exists" in response.json()["message"]


def test_verification_status(client, tokens):
    provision(
        client,
        tokens,
        "verify-token",
        uid="fb-verify",
        email="verify@example.com",
        email_verified=True,
    )
    response = client.get("/api/v1/auth/verification-status", headers=auth_header("verify-token"))
    assert response.status_code == 200
    assert response.json()["data"]["verified"] is True


def test_logout_revokes_existing_session(client, tokens):
    provision(client, tokens, "logout-token", uid="fb-logout", email="logout@example.com", auth_time=1_700_000_000)
    response = client.post("/api/v1/auth/logout", headers=auth_header("logout-token"))
    assert response.status_code == 200
    # Same token still has an older auth_time than token_invalidated_at.
    revoked = client.get("/api/v1/users/me", headers=auth_header("logout-token"))
    assert revoked.status_code == 401
    assert revoked.json()["error_code"] == ErrorCode.AUTH_SESSION_REVOKED


def test_session_bootstrap(client, tokens):
    provision(client, tokens, "session-token", uid="fb-session", email="session@example.com")
    response = client.get("/api/v1/auth/session", headers=auth_header("session-token"))
    assert response.status_code == 200
    assert response.json()["data"]["user"]["email"] == "session@example.com"
