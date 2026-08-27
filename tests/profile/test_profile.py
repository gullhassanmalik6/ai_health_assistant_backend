"""Profile, allergy, condition, and medication tests including ownership."""

from datetime import date, timedelta
from uuid import uuid4

from app.core.constants import ErrorCode
from tests.helpers import auth_header, provision


def test_get_empty_profile(client, tokens):
    provision(client, tokens, "p-token", uid="fb-profile", email="profile@example.com", name="Ada")
    response = client.get("/api/v1/profile", headers=auth_header("p-token"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Ada"
    assert data["allergies"] == []
    assert data["profile_completed"] is False


def test_put_and_get_profile(client, tokens):
    provision(client, tokens, "p2-token", uid="fb-p2", email="p2@example.com", name="Ada")
    payload = {
        "name": "Ada Lovelace",
        "gender": "female",
        "date_of_birth": "1995-04-10",
        "height": {"value": 168, "unit": "cm"},
        "weight": {"value": 62, "unit": "kg"},
        "blood_group": "O+",
        "emergency_contact_name": "Parent",
        "emergency_contact_phone": "+14155552671",
    }
    response = client.put("/api/v1/profile", headers=auth_header("p2-token"), json=payload)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["gender"] == "female"
    assert data["height"]["value"] == 168
    assert data["height"]["unit"] == "cm"
    assert data["blood_group"] == "O+"
    assert data["profile_completed"] is True
    assert data["profile_completion_percentage"] == 100


def test_patch_profile_partial(client, tokens):
    provision(client, tokens, "p3-token", uid="fb-p3", email="p3@example.com")
    client.patch(
        "/api/v1/profile",
        headers=auth_header("p3-token"),
        json={"gender": "male"},
    )
    response = client.patch(
        "/api/v1/profile",
        headers=auth_header("p3-token"),
        json={"blood_group": "A-"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["gender"] == "male"
    assert data["blood_group"] == "A-"


def test_invalid_future_dob(client, tokens):
    provision(client, tokens, "dob-token", uid="fb-dob", email="dob@example.com")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = client.patch(
        "/api/v1/profile",
        headers=auth_header("dob-token"),
        json={"date_of_birth": tomorrow},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == ErrorCode.VALIDATION_ERROR


def test_invalid_weight(client, tokens):
    provision(client, tokens, "w-token", uid="fb-w", email="w@example.com")
    response = client.patch(
        "/api/v1/profile",
        headers=auth_header("w-token"),
        json={"weight": {"value": -10, "unit": "kg"}},
    )
    assert response.status_code == 422


def test_invalid_height(client, tokens):
    provision(client, tokens, "h-token", uid="fb-h", email="h@example.com")
    response = client.patch(
        "/api/v1/profile",
        headers=auth_header("h-token"),
        json={"height": {"value": 12, "unit": "cm"}},
    )
    assert response.status_code == 422


def test_invalid_blood_group(client, tokens):
    provision(client, tokens, "bg-token", uid="fb-bg", email="bg@example.com")
    response = client.patch(
        "/api/v1/profile",
        headers=auth_header("bg-token"),
        json={"blood_group": "Z+"},
    )
    assert response.status_code == 422


def test_profile_completion_endpoint(client, tokens):
    provision(client, tokens, "c-token", uid="fb-c", email="c@example.com", name="Named")
    response = client.get("/api/v1/profile/completion", headers=auth_header("c-token"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["percentage"] > 0
    assert "name" in data["completed"]
    assert "blood_group" in data["missing"]


def test_reset_profile_does_not_delete_account(client, tokens):
    provision(client, tokens, "r-token", uid="fb-r", email="r@example.com", name="Keep Me")
    client.patch(
        "/api/v1/profile",
        headers=auth_header("r-token"),
        json={"gender": "other", "blood_group": "B+"},
    )
    response = client.delete("/api/v1/profile", headers=auth_header("r-token"))
    assert response.status_code == 200
    me = client.get("/api/v1/users/me", headers=auth_header("r-token"))
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "r@example.com"
    profile = client.get("/api/v1/profile", headers=auth_header("r-token"))
    assert profile.json()["data"]["gender"] is None


def test_allergy_crud_and_ownership(client, tokens):
    provision(client, tokens, "a-token", uid="fb-a", email="a@example.com")
    provision(client, tokens, "b-token", uid="fb-b", email="b@example.com")

    created = client.post(
        "/api/v1/profile/allergies",
        headers=auth_header("a-token"),
        json={"allergy_name": "Pollen", "severity": "moderate"},
    )
    assert created.status_code == 201
    allergy_id = created.json()["data"]["id"]

    listed = client.get("/api/v1/profile/allergies", headers=auth_header("a-token"))
    assert len(listed.json()["data"]) == 1

    updated = client.put(
        f"/api/v1/profile/allergies/{allergy_id}",
        headers=auth_header("a-token"),
        json={"allergy_name": "Dust", "severity": "severe"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["allergy_name"] == "Dust"

    other_list = client.get("/api/v1/profile/allergies", headers=auth_header("b-token"))
    assert other_list.json()["data"] == []

    stolen = client.delete(
        f"/api/v1/profile/allergies/{allergy_id}",
        headers=auth_header("b-token"),
    )
    assert stolen.status_code == 404
    assert stolen.json()["error_code"] == ErrorCode.NOT_FOUND

    unknown = client.delete(
        f"/api/v1/profile/allergies/{uuid4()}",
        headers=auth_header("a-token"),
    )
    assert unknown.status_code == 404

    deleted = client.delete(
        f"/api/v1/profile/allergies/{allergy_id}",
        headers=auth_header("a-token"),
    )
    assert deleted.status_code == 200
    empty = client.get("/api/v1/profile/allergies", headers=auth_header("a-token"))
    assert empty.json()["data"] == []


def test_condition_crud_and_ownership(client, tokens):
    provision(client, tokens, "ca-token", uid="fb-ca", email="ca@example.com")
    provision(client, tokens, "cb-token", uid="fb-cb", email="cb@example.com")

    created = client.post(
        "/api/v1/profile/conditions",
        headers=auth_header("ca-token"),
        json={"condition_name": "Asthma", "status": "managed"},
    )
    assert created.status_code == 201
    condition_id = created.json()["data"]["id"]

    listed = client.get("/api/v1/profile/conditions", headers=auth_header("ca-token"))
    assert len(listed.json()["data"]) == 1

    updated = client.put(
        f"/api/v1/profile/conditions/{condition_id}",
        headers=auth_header("ca-token"),
        json={"condition_name": "Asthma", "status": "active"},
    )
    assert updated.json()["data"]["status"] == "active"

    stolen = client.put(
        f"/api/v1/profile/conditions/{condition_id}",
        headers=auth_header("cb-token"),
        json={"condition_name": "Hacked"},
    )
    assert stolen.status_code == 404

    deleted = client.delete(
        f"/api/v1/profile/conditions/{condition_id}",
        headers=auth_header("ca-token"),
    )
    assert deleted.status_code == 200


def test_medication_crud_and_ownership(client, tokens):
    provision(client, tokens, "ma-token", uid="fb-ma", email="ma@example.com")
    provision(client, tokens, "mb-token", uid="fb-mb", email="mb@example.com")

    created = client.post(
        "/api/v1/profile/medications",
        headers=auth_header("ma-token"),
        json={
            "medication_name": "Metformin",
            "dosage": "500mg",
            "frequency": "twice daily",
            "route": "oral",
        },
    )
    assert created.status_code == 201
    medication_id = created.json()["data"]["id"]

    listed = client.get("/api/v1/profile/medications", headers=auth_header("ma-token"))
    assert listed.json()["data"][0]["medication_name"] == "Metformin"

    stolen = client.delete(
        f"/api/v1/profile/medications/{medication_id}",
        headers=auth_header("mb-token"),
    )
    assert stolen.status_code == 404

    deleted = client.delete(
        f"/api/v1/profile/medications/{medication_id}",
        headers=auth_header("ma-token"),
    )
    assert deleted.status_code == 200
