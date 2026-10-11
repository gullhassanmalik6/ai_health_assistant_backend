"""Change password for signed-in email accounts."""

from app.core.constants import AuthProvider, ErrorCode
from tests.helpers import auth_header, provision


def test_change_password_success(client, tokens):
    provision(client, tokens, "pw-token", uid="fb-pw", email="pw@example.com")
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header("pw-token"),
        json={"current_password": "Sup3rSecret", "new_password": "healthy2026"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["tokens"]["id_token"]
    assert data["tokens"]["refresh_token"]


def test_change_password_wrong_current(client, tokens):
    provision(client, tokens, "pw2-token", uid="fb-pw2", email="pw2@example.com")
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header("pw2-token"),
        json={"current_password": "wrong-password", "new_password": "healthy2026"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == ErrorCode.AUTH_INVALID_CURRENT_PASSWORD
    assert body["details"]["current_password"] == "Current password is incorrect"


def test_change_password_unchanged(client, tokens):
    provision(client, tokens, "pw3-token", uid="fb-pw3", email="pw3@example.com")
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header("pw3-token"),
        json={"current_password": "samepass1", "new_password": "samepass1"},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorCode.AUTH_PASSWORD_UNCHANGED


def test_change_password_guest_forbidden(client, tokens):
    provision(
        client,
        tokens,
        "guest-pw",
        uid="fb-guest-pw",
        email=None,
        provider=AuthProvider.ANONYMOUS,
    )
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header("guest-pw"),
        json={"current_password": "oldpass12", "new_password": "healthy2026"},
    )
    assert response.status_code == 403
    assert response.json()["error_code"] == ErrorCode.AUTH_PASSWORD_NOT_SUPPORTED
