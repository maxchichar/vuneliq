import pytest

from app.modules.ai.rate_limit import AIRateLimitError, RateLimiter, limiter
from app.shared.config import settings

def get_token(client, email: str) -> str:
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

class FakeClock:
    """Time we control by hand, so tests never wait."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_blocks_after_per_minute_limit():
    clock = FakeClock()
    rl = RateLimiter(clock=clock)
    for _ in range(3):
        rl.check("user1", per_minute=3, per_day=100)
    with pytest.raises(AIRateLimitError):
        rl.check("user1", per_minute=3, per_day=100)


def test_allows_again_after_a_minute():
    clock = FakeClock()
    rl = RateLimiter(clock=clock)
    for _ in range(3):
        rl.check("user1", per_minute=3, per_day=100)
    clock.now += 61  # a minute passes
    rl.check("user1", per_minute=3, per_day=100)  # must not raise


def test_daily_limit_blocks_even_when_minute_is_free():
    clock = FakeClock()
    rl = RateLimiter(clock=clock)
    for _ in range(4):
        rl.check("user1", per_minute=2, per_day=4)
        clock.now += 61  # stay under the per-minute limit
    with pytest.raises(AIRateLimitError):
        rl.check("user1", per_minute=2, per_day=4)


def test_users_are_counted_separately():
    rl = RateLimiter(clock=FakeClock())
    rl.check("user1", per_minute=1, per_day=10)
    rl.check("user2", per_minute=1, per_day=10)  # different user: fine


def test_router_returns_429_with_retry_after(client, monkeypatch):
    limiter.reset()  # start clean
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_PER_MINUTE", 2)
    token = get_token(client, "ratelimit@vuneliq.org")
    headers = {"Authorization": f"Bearer {token}"}
    body = {"text": "Wells built in three villages"}

    assert client.post("/api/ai/summarize", json=body, headers=headers).status_code == 200
    assert client.post("/api/ai/summarize", json=body, headers=headers).status_code == 200
    res = client.post("/api/ai/summarize", json=body, headers=headers)

    assert res.status_code == 429
    assert int(res.headers["Retry-After"]) > 0
    limiter.reset()