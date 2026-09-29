from collections import Counter

import httpx
import pytest
from fastapi.testclient import TestClient

from App.core.config import Settings
from App.main import create_app


def pokemon(name, types, attack=100, special=80, speed=100):
    return {"name": name, "types": [{"type": {"name": t}} for t in types], "stats": [
        {"stat": {"name": key}, "base_stat": value}
        for key, value in (("attack", attack), ("special-attack", special), ("speed", speed))
    ]}


def type_data(name, double=(), half=(), immune=(), pool=()):
    return {"name": name, "damage_relations": {
        key: [{"name": t} for t in values]
        for key, values in (("double_damage_from", double), ("half_damage_from", half), ("no_damage_from", immune))
    }, "pokemon": [{"pokemon": {"name": p}} for p in pool]}


@pytest.fixture
def upstream():
    data = {
        "pokemon/charizard": pokemon("charizard", ["fire", "flying"]),
        "pokemon/golem": pokemon("golem", ["rock", "ground"], 120, 55, 45),
        "pokemon/rhyperior": pokemon("rhyperior", ["ground", "rock"], 140, 55, 40),
        "pokemon/blastoise": pokemon("blastoise", ["water"], 83, 85, 78),
        "pokemon/pikachu": pokemon("pikachu", ["electric"], 55, 50, 90),
        "pokemon/venusaur": pokemon("venusaur", ["grass", "poison"], 82, 100, 80),
        "type/fire": type_data("fire", ["water", "ground", "rock"], ["fire", "grass", "ice", "bug", "steel", "fairy"]),
        "type/flying": type_data("flying", ["electric", "ice", "rock"], ["grass", "fighting", "bug"], ["ground"]),
        "type/water": type_data("water", ["electric", "grass"], ["fire", "water", "ice", "steel"], pool=["blastoise"]),
        "type/rock": type_data("rock", pool=["charizard", "golem", "rhyperior", "golem"]),
        "type/electric": type_data("electric", ["ground"], pool=["pikachu"]),
        "type/grass": type_data("grass", pool=["venusaur"]),
        "type/normal": type_data("normal", ["fighting"], immune=["ghost"]),
    }
    calls = Counter()
    state = {"fail": False, "data": data, "calls": calls}

    def handler(request):
        key = request.url.path.removeprefix("/api/v2/").strip("/")
        calls[key] += 1
        if state["fail"]:
            raise httpx.ReadTimeout("simulated private upstream detail", request=request)
        return httpx.Response(200, json=data[key]) if key in data else httpx.Response(404)

    state["handler"] = handler
    return state


@pytest.fixture
def client(upstream):
    app = create_app(Settings(pokeapi_retries=0, rate_limit_per_minute=100), httpx.MockTransport(upstream["handler"]))
    with TestClient(app) as client:
        yield client
