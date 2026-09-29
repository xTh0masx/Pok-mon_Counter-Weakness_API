import httpx
import pytest

from App.core.config import Settings
from App.services.pokeapi_client import NotFound, PokeAPIClient, UpstreamUnavailable
from conftest import pokemon


@pytest.mark.asyncio
async def test_retry_recovers_from_503():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503) if len(calls) == 1 else httpx.Response(200, json=pokemon("pikachu", ["electric"]))

    async with httpx.AsyncClient(base_url="https://pokeapi.co/api/v2/", transport=httpx.MockTransport(handler)) as http:
        client = PokeAPIClient(Settings(pokeapi_retries=1), http)
        result = await client.get("pokemon", "pikachu")
        assert result.source == "pokeapi"
        assert len(calls) == 2


@pytest.mark.asyncio
async def test_retries_are_bounded_and_circuit_avoids_more_requests():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(500)

    async with httpx.AsyncClient(base_url="https://pokeapi.co/api/v2/", transport=httpx.MockTransport(handler)) as http:
        client = PokeAPIClient(Settings(pokeapi_retries=1), http)
        for name in ("pikachu", "charizard"):
            with pytest.raises(UpstreamUnavailable):
                await client.get("pokemon", name)
        assert len(calls) == 2


@pytest.mark.asyncio
async def test_404_does_not_use_stale_cache_or_retry():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(404)

    async with httpx.AsyncClient(base_url="https://pokeapi.co/api/v2/", transport=httpx.MockTransport(handler)) as http:
        client = PokeAPIClient(Settings(), http)
        clock = [0.0]
        client.cache.clock = lambda: clock[0]
        client.cache.put("pokemon/pikachu", pokemon("pikachu", ["electric"]))
        clock[0] = client.cache.ttl + 1
        with pytest.raises(NotFound):
            await client.get("pokemon", "pikachu")
        assert client.cache.get("pokemon/pikachu", allow_stale=True) is None
        assert len(calls) == 1


@pytest.mark.asyncio
async def test_invalid_json_and_missing_stats_are_safe():
    for response in (httpx.Response(200, text="not json"), httpx.Response(200, json={"name": "pikachu", "types": [{"type": {"name": "electric"}}], "stats": []})):
        async with httpx.AsyncClient(base_url="https://pokeapi.co/api/v2/", transport=httpx.MockTransport(lambda request: response)) as http:
            client = PokeAPIClient(Settings(pokeapi_retries=0), http)
            with pytest.raises(UpstreamUnavailable):
                await client.get("pokemon", "pikachu")
            assert not client.cache.entries
