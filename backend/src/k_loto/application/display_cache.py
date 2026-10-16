"""Short, single-flight cache for public display aggregates only."""

import asyncio
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from datetime import datetime
from time import monotonic


class DisplayCache[K, V]:
    """Bounded worker-local single-flight cache. Never store personal data here."""

    def __init__(self, *, seconds: float, capacity: int = 32) -> None:
        self.seconds = seconds
        self.capacity = capacity
        self.lock = asyncio.Lock()
        self.values: OrderedDict[K, tuple[float, V]] = OrderedDict()

    async def get(self, key: K, load: Callable[[], Awaitable[V]]) -> V:
        async with self.lock:
            cached = self.values.get(key)
            if cached is not None and monotonic() < cached[0]:
                self.values.move_to_end(key)
                return cached[1]
            value = await load()
            self.values[key] = (monotonic() + self.seconds, value)
            self.values.move_to_end(key)
            while len(self.values) > self.capacity:
                self.values.popitem(last=False)
            return value


class PlatformTotalsCache:
    def __init__(self, *, seconds: float = 15) -> None:
        self.seconds = seconds
        self.lock = asyncio.Lock()
        self.key: datetime | None = None
        self.value: tuple[int, int, int] | None = None
        self.until = 0.0

    async def get(
        self, key: datetime, load: Callable[[], Awaitable[tuple[int, int, int]]]
    ) -> tuple[int, int, int]:
        async with self.lock:
            if self.key == key and self.value is not None and monotonic() < self.until:
                return self.value
            value = await load()
            self.key, self.value, self.until = key, value, monotonic() + self.seconds
            return value
