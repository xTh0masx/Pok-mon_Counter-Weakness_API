import httpx
import pytest
from fastapi.testclient import TestClient

from App.core.config import Settings
from App.core.middleware import RateLimiter
from App.main import create_app


@pytest.mark.parametrize("payload", [
    {"query": ""}, {"query": "   "}, {"query": "a" * 51},
    {"query": "../secret"}, {"query": "https://example.com"}, {"query": "gluräk"},
    {"query": "-fire"}, {"query": "fire", "input_type": "other"},
    {"query": "fire", "limit": 0}, {"query": "fire", "limit": 11},
    {"query": "fire", "limit": True}, {"query": "fire", "limit": "5"},
    {"query": "fire", "extra": "secret"}, {"query": 123},
])
def test_invalid_input(client, upstream, payload):
    assert client.post("/api/v1/analyze", json=payload).status_code == 422
    assert not upstream["calls"]


def test_rate_limit_and_health_exemption(upstream):
    app = create_app(Settings(rate_limit_per_minute=2), httpx.MockTransport(upstream["handler"]))
    with TestClient(app) as client:
        for _ in range(2):
            assert client.post("/api/v1/analyze", json={}).status_code == 422
        response = client.post("/api/v1/analyze", json={})
        assert response.status_code == 429
        assert int(response.headers["retry-after"]) > 0
        assert client.get("/health").status_code == 200


def test_rate_limit_window_and_capacity():
    clock = [0.0]
    limiter = RateLimiter(1, clock=lambda: clock[0], capacity=1)
    assert limiter.retry_after("a") == 0
    assert limiter.retry_after("a") == 60
    assert limiter.retry_after("b") == 60
    clock[0] = 60
    assert limiter.retry_after("b") == 0
    assert len(limiter.clients) == 1


def test_body_limit(client, upstream):
    assert client.post("/api/v1/analyze", content=b"x" * 8193).status_code == 413
    assert not upstream["calls"]


def test_cors_not_enabled(client):
    response = client.options("/api/v1/analyze", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in response.headers


def test_no_input_echo_in_error(client):
    response = client.post("/api/v1/analyze", json={"query": "private/value"})
    assert "private/value" not in response.text


def test_internal_error_is_generic(client, monkeypatch):
    async def broken(*args):
        raise RuntimeError("secret internal path")
    monkeypatch.setattr(client.app.state.pokeapi, "get", broken)
    response = client.post("/api/v1/analyze", json={"query": "water"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert response.headers["x-correlation-id"]
