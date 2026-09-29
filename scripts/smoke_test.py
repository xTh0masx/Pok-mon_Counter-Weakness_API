"""Explicit live checks: python scripts/smoke_test.py [--base-url URL].

Without --base-url, exercises the application locally against the real PokéAPI
and compares all fallback type relations with the upstream data.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from time import perf_counter

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from App.main import create_app
from App.services.type_chart import TYPE_CHART, fallback_type


async def check_api(http):
    assert (await http.get("/health")).json() == {"status": "ok"}
    assert (await http.get("/docs")).status_code == 200
    first = await http.post("/api/v1/analyze", json={"query": "charizard", "limit": 3})
    first.raise_for_status()
    data = first.json()
    assert data["target_types"] == ["fire", "flying"]
    assert {w["type"]: w["multiplier"] for w in data["weaknesses"]} == {"rock": 4, "water": 2, "electric": 2}
    assert 0 < len(data["recommended_pokemon"]) <= 3
    started = perf_counter()
    second = await http.post("/api/v1/analyze", json={"query": "charizard", "limit": 3})
    elapsed = (perf_counter() - started) * 1000
    second.raise_for_status()
    assert second.json()["cache_used"] is True
    assert (await http.post("/api/v1/analyze", json={"query": "not-a-pokemon"})).status_code == 404
    assert (await http.post("/api/v1/analyze", json={"query": "../bad"})).status_code == 422
    ready = await http.get("/ready")
    ready.raise_for_status()
    print(json.dumps({"analysis": data, "cached_request_ms": round(elapsed, 2), "ready": ready.json()}, indent=2))


async def main(base_url):
    if base_url:
        async with httpx.AsyncClient(base_url=base_url, timeout=60) as http:
            await check_api(http)
        return
    app = create_app()
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
            await check_api(http)
        for name in TYPE_CHART:
            resource = await app.state.pokeapi.get("type", name)
            assert resource.source != "fallback" and not resource.warning, f"Live chart check unavailable: {name}"
            for relation, expected in fallback_type(name)["damage_relations"].items():
                assert {t["name"] for t in resource.data["damage_relations"][relation]} == {t["name"] for t in expected}, (name, relation)
        print("All 18 fallback types match PokeAPI.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", help="Existing deployed API URL (does not deploy anything)")
    asyncio.run(main(parser.parse_args().base_url))
