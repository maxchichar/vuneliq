from fastapi.testclient import TestClient

def test_health_check_returns_healthy(client: TestClient):
    """Verify that the /health endpoint returns 200 OK and expected status."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Vuneliq API" in data["app"]