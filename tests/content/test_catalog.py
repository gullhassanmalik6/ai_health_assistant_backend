"""Categories, concerns, health tips, daily tip, and notifications."""

from tests.helpers import auth_header, provision


def test_categories_list_and_detail(client, tokens):
    provision(client, tokens, "cat-token", uid="fb-cat", email="cat@example.com")
    listed = client.get("/api/v1/categories", headers=auth_header("cat-token"))
    assert listed.status_code == 200
    items = listed.json()["data"]["items"]
    assert len(items) == 17
    assert items[0]["slug"] == "general-physician"
    assert items[1]["slug"] == "cardiologist"
    assert items[1]["icon_key"] == "cardiologist"
    assert items[1]["tint_key"] == "coral"

    missing = client.get("/api/v1/categories/not-a-doctor", headers=auth_header("cat-token"))
    assert missing.status_code == 404

    detail = client.get("/api/v1/categories/cardiologist", headers=auth_header("cat-token"))
    assert detail.status_code == 200
    data = detail.json()["data"]
    assert data["ai_title"] == "AI Cardiologist"
    assert [item["id"] for item in data["concerns"]] == [
        "chest-pain",
        "high-blood-pressure",
        "rapid-heartbeat",
    ]
    assert data["health_tips"][0]["id"] == "heart-health-tips"


def test_concern_and_health_tip_detail(client, tokens):
    provision(client, tokens, "c2-token", uid="fb-c2", email="c2@example.com")
    concern = client.get("/api/v1/concerns/chest-pain", headers=auth_header("c2-token"))
    assert concern.status_code == 200
    data = concern.json()["data"]
    assert data["category"]["slug"] == "cardiologist"
    assert "Pressure, squeezing or tightness in the chest" in data["symptoms"]
    assert client.get("/api/v1/concerns/missing", headers=auth_header("c2-token")).status_code == 404

    tip = client.get("/api/v1/health-tips/heart-health-tips", headers=auth_header("c2-token"))
    assert tip.status_code == 200
    assert "Walk or exercise 30 minutes most days" in tip.json()["data"]["daily_habits"]
    assert client.get("/api/v1/health-tips/missing", headers=auth_header("c2-token")).status_code == 404


def test_daily_tip_and_unread_count(client, tokens):
    provision(client, tokens, "tip-token", uid="fb-tip", email="tip@example.com")
    daily = client.get(
        "/api/v1/health-tips/daily",
        headers={**auth_header("tip-token"), "X-Timezone": "UTC"},
    )
    assert daily.status_code == 200
    assert daily.json()["data"]["date"]
    assert daily.json()["data"]["text"]

    badge = client.get("/api/v1/notifications/unread-count", headers=auth_header("tip-token"))
    assert badge.status_code == 200
    assert badge.json()["data"]["count"] == 0
