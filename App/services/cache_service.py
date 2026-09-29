"""Bounded LRU cache with fresh and time-limited stale entries."""

from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic
from typing import Callable, Any


@dataclass
class Entry:
    value: Any
    expires: float


class TTLCache:
    def __init__(self, ttl: float, stale: float, capacity: int, clock: Callable = monotonic):
        self.ttl, self.stale, self.capacity, self.clock = ttl, stale, capacity, clock
        self.entries: OrderedDict[str, Entry] = OrderedDict()

    def get(self, key: str, *, allow_stale: bool = False) -> Any | None:
        entry = self.entries.get(key)
        if entry is None:
            return None
        now = self.clock()
        if now >= entry.expires + self.stale:
            del self.entries[key]
            return None
        if now >= entry.expires and not allow_stale:
            return None
        self.entries.move_to_end(key)
        return entry.value

    def put(self, key: str, value: Any) -> None:
        self.entries[key] = Entry(value, self.clock() + self.ttl)
        self.entries.move_to_end(key)
        while len(self.entries) > self.capacity:
            self.entries.popitem(last=False)

    def discard(self, key: str) -> None:
        self.entries.pop(key, None)
