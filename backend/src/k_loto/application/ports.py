"""Interfaces used by application services."""

from collections.abc import AsyncIterator, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID


class SecureNumberGenerator(Protocol):
    def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]: ...

    def draw_sequence(
        self, minimum: int, maximum: int, length: int
    ) -> tuple[int, ...]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class TransactionBoundary(Protocol):
    def begin(self) -> AbstractAsyncContextManager[object]: ...


class PlayerNotifier(Protocol):
    async def tickets_purchased(
        self, user_id: UUID, ticket_ids: Sequence[UUID]
    ) -> None: ...

    async def draw_completed(self, draw_id: UUID, user_ids: Sequence[UUID]) -> None: ...


class NotificationOutbox(Protocol):
    def pending(self) -> AsyncIterator[object]: ...
