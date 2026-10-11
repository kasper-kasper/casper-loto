"""Short, single-flight cache for public display aggregates only."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from time import monotonic


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
