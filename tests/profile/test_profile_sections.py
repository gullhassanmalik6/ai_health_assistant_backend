"""Personal/health section writes, photos, completion, and field-level errors."""

from app.core.constants import ErrorCode
from tests.helpers import auth_header, provision

MIN_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


def test_completion_ignores_emergency_contact(client, tokens):
    provision(client, tokens, "comp-token", uid="fb-comp", email="comp@example.com", name="Humaira")
    client.patch(
        "/api/v1/profile/personal",
        headers=auth_header("comp-token"),
        json={"date_of_birth": "1998-04-12", "gender": "female"},
    )
    client.patch(
        "/api/v1/profile/health",
        headers=auth_header("comp-token"),
        json={
            "height": {"value": 165, "unit": "cm"},
            "weight": {"value": 55, "unit": "kg"},
            "blood_group": "unknown",
        },
    )
    response = client.get("/api/v1/profile/completion", headers=auth_header("comp-token"))
    data = response.json()["data"]
    assert data["percentage"] == 100
    assert data["is_complete"] is True
    assert "emergency_contact" not in data["completed"]
    assert "emergency_contact" not in data["missing"]


def test_personal_and_health_partial_and_clear(client, tokens):
    provision(client, tokens, "sec-token", uid="fb-sec", email="sec@example.com", name="Ada")
    empty = client.patch(
        "/api/v1/profile/personal",
        headers=auth_header("sec-token"),
        json={},
    )
    assert empty.status_code == 200
    assert empty.json()["data"]["name"] == "Ada"

    cleared_name = client.patch(
        "/api/v1/profile/personal",
        headers=auth_header("sec-token"),
        json={"name": None},
    )
    assert cleared_name.status_code == 422
    assert cleared_name.json()["details"]["name"] == "Enter your full name"

    saved = client.patch(
        "/api/v1/profile/personal",
        headers=auth_header("sec-token"),
        json={"name": "Humaira Khan", "gender": "female", "date_of_birth": "1998-04-12"},
    )
    assert saved.status_code == 200
    assert saved.json()["data"]["name"] == "Humaira Khan"

    health = client.patch(
        "/api/v1/profile/health",
        headers=auth_header("sec-token"),
        json={
            "blood_group": "B+",
            "allergies": ["Dust", "Pollen", "dust"],
            "conditions": ["Asthma"],
        },
    )
    assert health.status_code == 200
    names = [item["allergy_name"] for item in health.json()["data"]["allergies"]]
    assert names == ["Dust", "Pollen"]
    assert health.json()["data"]["allergies"][0]["severity"] == "unknown"

    keep = client.patch(
        "/api/v1/profile/health",
        headers=auth_header("sec-token"),
        json={"allergies": ["Pollen", "Ragweed"]},
    )
    names = [item["allergy_name"] for item in keep.json()["data"]["allergies"]]
    assert names == ["Pollen", "Ragweed"]
    pollen = next(item for item in keep.json()["data"]["allergies"] if item["allergy_name"] == "Pollen")
    assert pollen["severity"] == "unknown"

    cleared = client.patch(
        "/api/v1/profile/health",
        headers=auth_header("sec-token"),
        json={"blood_group": None, "allergies": []},
    )
    assert cleared.json()["data"]["blood_group"] is None
    assert cleared.json()["data"]["allergies"] == []


def test_blood_group_unknown_accepted(client, tokens):
    provision(client, tokens, "bg2-token", uid="fb-bg2", email="bg2@example.com")
    response = client.patch(
        "/api/v1/profile",
        headers=auth_header("bg2-token"),
        json={"blood_group": "unknown"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["blood_group"] == "unknown"


def test_validation_details_are_field_map(client, tokens):
    provision(client, tokens, "val-token", uid="fb-val", email="val@example.com")
    response = client.patch(
        "/api/v1/profile/health",
        headers=auth_header("val-token"),
        json={"height": {"value": 12, "unit": "cm"}},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == ErrorCode.VALIDATION_ERROR
    assert body["message"] == "Please check the highlighted fields."
    assert isinstance(body["details"], dict)
    assert "height" in body["details"]
    assert not body["details"]["height"].endswith(".")


def test_photo_upload_and_delete(client, tokens):
    provision(client, tokens, "photo-token", uid="fb-photo", email="photo@example.com")
    bad = client.post(
        "/api/v1/profile/photo",
        headers=auth_header("photo-token"),
        files={"file": ("note.txt", b"not-an-image", "text/plain")},
    )
    assert bad.status_code == 422
    assert bad.json()["details"]["file"].startswith("Use a JPG")

    huge = client.post(
        "/api/v1/profile/photo",
        headers=auth_header("photo-token"),
        files={"file": ("big.jpg", b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024 + 1), "image/jpeg")},
    )
    assert huge.status_code == 422

    uploaded = client.post(
        "/api/v1/profile/photo",
        headers=auth_header("photo-token"),
        files={"file": ("me.jpg", MIN_JPEG, "image/jpeg")},
    )
    assert uploaded.status_code == 200
    url = uploaded.json()["data"]["profile_photo_url"]
    assert url
    assert uploaded.json()["data"]["profile_photo_expires_at"]

    deleted = client.delete("/api/v1/profile/photo", headers=auth_header("photo-token"))
    assert deleted.status_code == 200
    assert deleted.json()["data"]["profile_photo_url"] is None
    again = client.delete("/api/v1/profile/photo", headers=auth_header("photo-token"))
    assert again.status_code == 200


def test_profile_setup_seen_flag(client, tokens):
    user = provision(client, tokens, "seen-token", uid="fb-seen", email="seen@example.com")
    assert user["profile_setup_seen"] is False
    response = client.patch(
        "/api/v1/users/me",
        headers=auth_header("seen-token"),
        json={"profile_setup_seen": True},
    )
    assert response.status_code == 200
    assert response.json()["data"]["profile_setup_seen"] is True
    session = client.get("/api/v1/auth/session", headers=auth_header("seen-token"))
    assert session.json()["data"]["user"]["profile_setup_seen"] is True
