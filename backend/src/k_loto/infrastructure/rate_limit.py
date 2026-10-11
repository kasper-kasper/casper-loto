"""Small bounded fixed-window limiter for the single production API process."""

from collections import defaultdict, deque
from time import monotonic
from uuid import UUID


class PurchaseRateLimiter:
    def __init__(self) -> None:
        self._events: dict[UUID, deque[float]] = defaultdict(deque)

    def allow(self, user_id: UUID, *, limit: int, window_seconds: int = 5) -> bool:
        now = monotonic()
        events = self._events[user_id]
        while events and events[0] <= now - window_seconds:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(now)
        if len(self._events) > 10_000:
            self._events = defaultdict(
                deque,
                {
                    key: value
                    for key, value in self._events.items()
                    if value and value[-1] > now - window_seconds
                },
            )
        return True


purchase_rate_limiter = PurchaseRateLimiter()
