from fastapi.testclient import TestClient

from changelens.api import app

client = TestClient(app)


def test_health_endpoint() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_dashboard_and_assets_are_served() -> None:
    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "Analyze changes" in dashboard.text
    assert client.get("/assets/app.css").status_code == 200
    assert client.get("/assets/app.js").status_code == 200


def test_named_demo_plan_is_available() -> None:
    response = client.get("/examples/delete_shared_database")
    assert response.status_code == 200
    assert response.json()["resource_changes"][0]["address"] == "aws_db_instance.shared"


def test_unknown_demo_plan_is_not_served() -> None:
    assert client.get("/examples/not-a-demo").status_code == 404


def test_analyze_endpoint_returns_report() -> None:
    response = client.post("/analyze", json={"resource_changes": []})
    assert response.status_code == 200
    assert response.json()["findings"] == []


def test_analyze_endpoint_rejects_malformed_plan() -> None:
    response = client.post(
        "/analyze",
        json={"resource_changes": [{"change": {"actions": ["delete"]}}]},
    )
    assert response.status_code == 422
