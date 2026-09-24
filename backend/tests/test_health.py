from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    # The database may or may not be running during tests; either answer is valid.
    assert body["database"] in {"ok", "unreachable"}
