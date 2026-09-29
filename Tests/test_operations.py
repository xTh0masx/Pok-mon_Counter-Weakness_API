import json
import logging

import pytest
from pydantic import ValidationError

from App.core.config import Settings
from App.core.logging import JSONFormatter
from App.services.analysis_service import AnalysisService


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("CACHE_TTL_SECONDS", "123")
    assert Settings.from_env().cache_ttl_seconds == 123


@pytest.mark.parametrize("settings", [
    {"pokeapi_base_url": "http://example.com"},
    {"pokeapi_base_url": "https://user:password@example.com"},
    {"cache_ttl_seconds": 0}, {"pokeapi_retries": 3},
    {"candidates_per_type": 100}, {"log_level": "INVALID"},
])
def test_bad_config_rejected(settings):
    with pytest.raises(ValidationError):
        Settings(**settings)


def test_json_logs_have_request_metadata(client):
    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(json.loads(JSONFormatter().format(record)))

    logger = logging.getLogger("pokemon")
    handler = Capture()
    logger.addHandler(handler)
    try:
        response = client.post("/api/v1/analyze", json={"query": "charizard"})
        cached = client.post("/api/v1/analyze", json={"query": "charizard"})
    finally:
        logger.removeHandler(handler)
    requests = [r for r in records if r["event"] == "request"]
    assert requests[0]["correlation_id"] == response.headers["x-correlation-id"]
    assert requests[1]["correlation_id"] == cached.headers["x-correlation-id"]
    assert requests[0]["correlation_id"] != requests[1]["correlation_id"]
    assert requests[0]["status"] == 200
    assert requests[0]["endpoint"] == "/api/v1/analyze"
    assert requests[0]["request_duration_ms"] >= 0
    assert any(r["event"] == "cache_hit" for r in records)


def test_analysis_deadline_returns_503(client, monkeypatch):
    async def timeout(*args):
        raise TimeoutError()
    monkeypatch.setattr(AnalysisService, "analyze", timeout)
    assert client.post("/api/v1/analyze", json={"query": "water"}).status_code == 503
