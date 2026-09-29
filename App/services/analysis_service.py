import asyncio

from App.models.schemas import AnalysisRequest, AnalysisResponse, Recommendation, Weakness
from App.services.pokeapi_client import NotFound, PokeAPIClient, Resource, UpstreamUnavailable
from App.services.type_chart import TYPE_CHART

TYPE_WEIGHT, OFFENSE_WEIGHT, SPEED_WEIGHT = 6, 3, 1
MAX_ATTACK_TYPES = 3


def effectiveness(type_resources: list[dict]) -> dict[str, float]:
    factors = dict.fromkeys(TYPE_CHART, 1.0)
    for resource in type_resources:
        for relation, multiplier in (("double_damage_from", 2), ("half_damage_from", 0.5), ("no_damage_from", 0)):
            for attacker in resource["damage_relations"][relation]:
                factors[attacker["name"]] *= multiplier
    return factors


def score_candidate(data: dict, factors: dict[str, float]) -> Recommendation:
    best_type = max((t["type"]["name"] for t in data["types"]), key=lambda t: (factors[t], t))
    factor = factors[best_type]
    stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    offense = max(stats["attack"], stats["special-attack"])
    speed = stats["speed"]
    score = round(min(factor, 4) / 4 * TYPE_WEIGHT + min(offense, 200) / 200 * OFFENSE_WEIGHT + min(speed, 200) / 200 * SPEED_WEIGHT, 2)
    return Recommendation(name=data["name"], score=score, reason=f"{best_type} is {factor:g}x effective; offense={offense}, speed={speed}")


class AnalysisService:
    def __init__(self, client: PokeAPIClient):
        self.client = client

    async def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        resources: list[Resource] = []
        warnings: list[str] = []

        async def fetch(kind: str, name: str) -> dict:
            resource = await self.client.get(kind, name)
            resources.append(resource)
            return resource.data

        is_type = request.input_type == "type" or (request.input_type == "auto" and request.query in TYPE_CHART)
        target = request.query
        if is_type:
            if target not in TYPE_CHART:
                raise NotFound()
            target_types = [target]
        else:
            pokemon = await fetch("pokemon", target)
            target = pokemon["name"]
            target_types = [item["type"]["name"] for item in pokemon["types"]]
        types = await asyncio.gather(*(fetch("type", name) for name in target_types))
        factors = effectiveness(types)
        weaknesses = sorted(
            (Weakness(type=name, multiplier=factor) for name, factor in factors.items() if factor > 1),
            key=lambda w: (-w.multiplier, w.type),
        )
        candidates: dict[str, None] = {}
        for weakness in weaknesses[:MAX_ATTACK_TYPES]:
            try:
                pool = await fetch("type", weakness.type)
            except (NotFound, UpstreamUnavailable):
                warnings.append("some counter types unavailable")
                continue
            added = 0
            for entry in pool["pokemon"]:
                name = entry["pokemon"]["name"]
                if name == target or name in candidates:
                    continue
                candidates[name] = None
                added += 1
                if added >= self.client.settings.candidates_per_type:
                    break

        async def candidate(name: str) -> Recommendation | None:
            try:
                data = await fetch("pokemon", name)
                if data["name"] == target:
                    return None
                result = score_candidate(data, factors)
                if max(factors[t["type"]["name"]] for t in data["types"]) > 1:
                    return result
            except (NotFound, UpstreamUnavailable):
                warnings.append("some counter Pokemon unavailable")
            return None

        results = await asyncio.gather(*(candidate(name) for name in candidates))
        unique = {r.name: r for r in results if r is not None}
        ranked = sorted(unique.values(), key=lambda r: (-r.score, r.name))[:request.limit]
        if not ranked:
            warnings.append("no counter recommendations available")
        sources = {r.source for r in resources}
        return AnalysisResponse(
            target=target, target_types=target_types, weaknesses=weaknesses,
            recommended_pokemon=ranked,
            source="fallback" if "fallback" in sources else "pokeapi" if "pokeapi" in sources else "cache",
            cache_used=any(r.cache_used for r in resources),
            warnings=sorted(set(warnings + [r.warning for r in resources if r.warning])),
        )
