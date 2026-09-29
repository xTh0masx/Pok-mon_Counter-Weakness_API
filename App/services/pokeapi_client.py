import asyncio
import logging
import re
from dataclasses import dataclass
from time import monotonic

import httpx
from pydantic import BaseModel, Field, ValidationError

from App.core.config import Settings
from App.services.cache_service import TTLCache
from App.services.type_chart import TYPE_CHART, fallback_type

logger = logging.getLogger("pokemon")


class NotFound(Exception):
    pass


class UpstreamUnavailable(Exception):
    pass


class Named(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TypeSlot(BaseModel):
    type: Named


class Stat(BaseModel):
    base_stat: int = Field(ge=0, le=1000)
    stat: Named


class PokemonResource(Named):
    types: list[TypeSlot] = Field(min_length=1, max_length=2)
    stats: list[Stat] = Field(min_length=1)


class Relations(BaseModel):
    double_damage_from: list[Named]
    half_damage_from: list[Named]
    no_damage_from: list[Named]


class PokemonSlot(BaseModel):
    pokemon: Named


class TypeResource(Named):
    damage_relations: Relations
    pokemon: list[PokemonSlot]


@dataclass
class Resource:
    data: dict
    source: str = "pokeapi"
    cache_used: bool = False
    warning: str | None = None


class PokeAPIClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient):
        self.settings, self.http = settings, http
        self.cache = TTLCache(settings.cache_ttl_seconds, settings.cache_stale_seconds, settings.cache_max_entries)
        self.semaphore = asyncio.Semaphore(5)
        self.unavailable_until = 0.0

    async def get(self, kind: str, name: str) -> Resource:
        if kind not in {"pokemon", "type"} or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise NotFound()
        key = f"{kind}/{name}"
        cached = self.cache.get(key)
        if cached is not None:
            logger.info("cache_hit", extra={"resource": key})
            return Resource(cached, "cache", True)
        async with self.semaphore:
            # Re-check after waiting; earlier requests may have populated the cache.
            cached = self.cache.get(key)
            if cached is not None:
                return Resource(cached, "cache", True)
            if monotonic() >= self.unavailable_until:
                for attempt in range(self.settings.pokeapi_retries + 1):
                    try:
                        async with asyncio.timeout(self.settings.pokeapi_timeout_seconds):
                            response = await self.http.get(key + "/")
                        if response.status_code == 404:
                            self.cache.discard(key)
                            raise NotFound()
                        response.raise_for_status()
                        model = PokemonResource if kind == "pokemon" else TypeResource
                        data = model.model_validate(response.json()).model_dump()
                        if kind == "pokemon":
                            if any(t["type"]["name"] not in TYPE_CHART for t in data["types"]):
                                raise ValueError("Unsupported type")
                            if not {"attack", "special-attack", "speed"} <= {s["stat"]["name"] for s in data["stats"]}:
                                raise ValueError("Missing base stats")
                        else:
                            if data["name"] != name or any(
                                t["name"] not in TYPE_CHART
                                for group in data["damage_relations"].values() for t in group
                            ):
                                raise ValueError("Invalid type relations")
                        self.cache.put(key, data)
                        return Resource(data)
                    except (httpx.HTTPError, TimeoutError, ValueError, ValidationError) as exc:
                        logger.warning("upstream_error", extra={"resource": key, "error_type": type(exc).__name__})
                        if attempt < self.settings.pokeapi_retries:
                            await asyncio.sleep(0.1 * 2**attempt)
                self.unavailable_until = monotonic() + 15
        stale = self.cache.get(key, allow_stale=True)
        if stale is not None:
            logger.warning("fallback_used", extra={"resource": key, "fallback": "stale_cache"})
            return Resource(stale, "cache", True, "stale cache used")
        if kind == "type" and name in TYPE_CHART:
            logger.warning("fallback_used", extra={"resource": key, "fallback": "local_type_chart"})
            return Resource(fallback_type(name), "fallback", False, "limited fallback: local type chart; counter data may be unavailable")
        raise UpstreamUnavailable()
