import asyncio
from datetime import UTC, datetime

import pytest

from k_loto.application.display_cache import PlatformTotalsCache


async def test_public_totals_single_flight_expiry_and_month_rollover(monkeypatch):
    clock = [1.0]
    monkeypatch.setattr("k_loto.application.display_cache.monotonic", lambda: clock[0])
    cache = PlatformTotalsCache(seconds=15)
    calls = 0

    async def load():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return (calls, 2, 3)

    month = datetime(2026, 10, 1, tzinfo=UTC)
    results = await asyncio.gather(*(cache.get(month, load) for _ in range(10)))
    assert calls == 1 and results == [(1, 2, 3)] * 10
    clock[0] = 16
    assert await cache.get(month, load) == (2, 2, 3)
    assert await cache.get(datetime(2026, 11, 1, tzinfo=UTC), load) == (3, 2, 3)


async def test_failure_is_not_cached():
    cache = PlatformTotalsCache()
    month = datetime(2026, 10, 1, tzinfo=UTC)

    async def failure():
        raise RuntimeError("unavailable")

    with pytest.raises(RuntimeError):
        await cache.get(month, failure)

    async def success():
        return (1, 2, 3)

    assert await cache.get(month, success) == (1, 2, 3)
