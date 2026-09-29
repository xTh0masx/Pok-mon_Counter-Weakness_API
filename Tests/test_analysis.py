from time import perf_counter

import pytest

from App.services.analysis_service import effectiveness, score_candidate
from App.services.type_chart import TYPE_CHART, fallback_type
from conftest import pokemon


def analyze(client, **kwargs):
    return client.post("/api/v1/analyze", json={"query": "charizard", **kwargs})


def test_charizard_and_counter_score(client):
    response = analyze(client)
    assert response.status_code == 200
    data = response.json()
    assert data["target_types"] == ["fire", "flying"]
    assert {w["type"]: w["multiplier"] for w in data["weaknesses"]} == {"rock": 4, "water": 2, "electric": 2}
    counters = data["recommended_pokemon"]
    assert counters[0]["name"] == "rhyperior"
    assert counters[0]["score"] == 8.3
    assert "4x" in counters[0]["reason"]
    assert [r["score"] for r in counters] == sorted((r["score"] for r in counters), reverse=True)
    assert len({r["name"] for r in counters}) == len(counters)
    assert "charizard" not in {r["name"] for r in counters}
    assert data["warnings"] == []


@pytest.mark.parametrize("mode", ["auto", "type"])
def test_water_type(client, mode):
    data = analyze(client, query=" WATER ", input_type=mode).json()
    assert data["target"] == "water"
    assert {w["type"] for w in data["weaknesses"]} == {"electric", "grass"}


def test_limit(client):
    assert len(analyze(client, limit=3).json()["recommended_pokemon"]) == 3


@pytest.mark.parametrize("query,mode", [("not-a-pokemon", "auto"), ("unknown", "type"), ("fire", "pokemon")])
def test_unknown(client, query, mode):
    assert analyze(client, query=query, input_type=mode).status_code == 404


def test_cache_reuses_all_upstream_data(client, upstream):
    analyze(client)
    before = upstream["calls"].copy()
    start = perf_counter()
    result = analyze(client).json()
    assert perf_counter() - start < 0.5
    assert result["cache_used"] is True
    assert result["source"] == "cache"
    assert upstream["calls"] == before


def test_stale_cache_on_timeout(client, upstream):
    cache = client.app.state.pokeapi.cache
    clock = [0.0]
    cache.clock = lambda: clock[0]
    analyze(client)
    clock[0] = cache.ttl + 1
    upstream["fail"] = True
    result = analyze(client)
    assert result.status_code == 200
    assert result.json()["source"] == "cache"
    assert "stale cache used" in result.json()["warnings"]
    assert result.json()["recommended_pokemon"]


def test_offline_type_fallback(client, upstream):
    upstream["fail"] = True
    data = analyze(client, query="water").json()
    assert data["source"] == "fallback"
    assert data["cache_used"] is False
    assert {w["type"] for w in data["weaknesses"]} == {"electric", "grass"}
    assert data["recommended_pokemon"] == []
    assert any("limited fallback" in w for w in data["warnings"])


def test_offline_unknown_pokemon_returns_safe_503(client, upstream):
    upstream["fail"] = True
    response = analyze(client)
    assert response.status_code == 503
    assert "private" not in response.text
    assert response.headers["retry-after"] == "15"


def test_partial_candidate_failure(client, upstream):
    del upstream["data"]["pokemon/rhyperior"]
    data = analyze(client).json()
    assert data["recommended_pokemon"]
    assert "some counter Pokemon unavailable" in data["warnings"]


def test_invalid_upstream_payload_uses_fallback(client, upstream):
    upstream["data"]["type/water"] = {"unexpected": "data"}
    response = analyze(client, query="water")
    assert response.status_code == 200
    assert response.json()["source"] == "fallback"


def test_immunity_and_resistance_multiply():
    factors = effectiveness([fallback_type("ground"), fallback_type("flying")])
    assert factors["electric"] == 0
    assert factors["ice"] == 4
    assert factors["rock"] == 1
    assert effectiveness([fallback_type("grass"), fallback_type("steel")])["grass"] == 0.25


def test_score_is_capped():
    assert score_candidate(pokemon("test", ["rock"], 300, 300, 300), {"rock": 4}).score == 10


def test_fallback_chart_is_complete():
    assert len(TYPE_CHART) == 18
    for name in TYPE_CHART:
        groups = [set(group.split()) for group in TYPE_CHART[name]]
        assert all(group <= TYPE_CHART.keys() for group in groups)
        assert sum(map(len, groups)) == len(set.union(*groups))
