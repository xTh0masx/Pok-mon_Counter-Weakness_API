from App.services.cache_service import TTLCache


def test_expiry_stale_and_eviction():
    clock = [0.0]
    cache = TTLCache(10, 20, 2, lambda: clock[0])
    cache.put("a", {"value": 1})
    clock[0] = 10
    assert cache.get("a") is None
    assert cache.get("a", allow_stale=True) == {"value": 1}
    clock[0] = 30
    assert cache.get("a", allow_stale=True) is None
    assert not cache.entries
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1
    cache.put("c", 3)
    assert cache.get("b") is None
    assert cache.get("a") == 1
