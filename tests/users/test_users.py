"""Current-user and account deletion tests."""

import uuid

from app.core.constants import ErrorCode
from tests.helpers import auth_header, provision


def test_get_me(client, tokens):
    user = provision(client, tokens, "me-token", uid="fb-me", email="me@example.com", name="Humaira")
    response = client.get("/api/v1/users/me", headers=auth_header("me-token"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == user["id"]
    assert data["name"] == "Humaira"
    assert "password" not in data
    assert "token_invalidated_at" not in data


def test_patch_me_onboarding(client, tokens):
    provision(client, tokens, "onboard-token", uid="fb-onboard", email="onboard@example.com")
    response = client.patch(
        "/api/v1/users/me",
        headers=auth_header("onboard-token"),
        json={"onboarding_completed": True, "name": "Updated Name"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["onboarding_completed"] is True
    assert data["name"] == "Updated Name"


def test_unauthorized_access_to_users_me(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_account_deletion_removes_data(client, tokens, firebase_mocks):
    user = provision(client, tokens, "del-token", uid="fb-delete", email="delete@example.com")
    client.post(
        "/api/v1/profile/allergies",
        headers=auth_header("del-token"),
        json={"allergy_name": "Pollen"},
    )
    response = client.delete("/api/v1/users/me", headers=auth_header("del-token"))
    assert response.status_code == 200
    assert "fb-delete" in firebase_mocks["deleted"]

    # Recreating from the same Firebase identity should not resurrect health data.
    again = provision(client, tokens, "del-token", uid="fb-delete", email="delete@example.com")
    assert again["id"] != user["id"]
    allergies = client.get("/api/v1/profile/allergies", headers=auth_header("del-token"))
    assert allergies.json()["data"] == []


def test_cannot_target_another_user_id(client, tokens):
    """Ownership is derived from the token. A client-supplied UUID is ignored."""
    provision(client, tokens, "self-token", uid="fb-self", email="self@example.com")
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/users/{fake_id}", headers=auth_header("self-token"))
    assert response.status_code == 404
