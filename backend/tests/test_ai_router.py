from fastapi.testclient import TestClient

from app.modules.ai.providers import AIProvider, AIProviderError


def get_token(client: TestClient, email: str = "donor_ai@vuneliq.org") -> str:
    """Register + login a donor, return the access token."""
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123",
              "full_name": "Test Donor", "role": "donor"},
    )
    res = client.post(
        "/api/auth/login", json={"email": email, "password": "password123"}
    )
    return res.json()["access_token"]
#it check if user is not logged in or the users lacks the necessary permission
def test_summarize_requires_login(client: TestClient):
    res = client.post("/api/ai/summarize", json={"text": "hello"})
    assert res.status_code in (401, 403) 

def test_summarize_works_with_mock_when_no_key(client: TestClient):
    token = get_token(client)
    res = client.post(
        "/api/ai/summarize",
        json={"text": "Wells built in three villages"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["is_mock"] is True  # honest label reaches the client

# this check for an empty text whether is return the status code
#   
def test_empty_text_returns_422(client: TestClient):
    token = get_token(client)
    res = client.post(
        "/api/ai/summarize",
        json={"text": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422
    
def test_provider_failure_returns_502_without_leaking_details(
    client: TestClient, monkeypatch
):
    class DownProvider(AIProvider):
        def summarize(self, text):
            raise AIProviderError("secret internal detail: key sk-123 rejected")

    monkeypatch.setattr("app.modules.ai.services.get_provider", lambda: DownProvider())
    token = get_token(client)
    res = client.post(
        "/api/ai/summarize",
        json={"text": "some text"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 502
    assert "sk-123" not in res.text  # internal details must not leak