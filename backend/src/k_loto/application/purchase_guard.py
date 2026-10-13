"""Serialize durable Mini App requests and fence cancelled, uncommitted attempts."""

import hashlib
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.errors import InvalidTicket
from k_loto.infrastructure.database.models import PurchaseCancellation


def bingo_purchase_key(user_id: UUID, key: str) -> str:
    """Keep the historical Bingo ledger namespace without losing the client key."""
    return hashlib.sha256(f"bingo:{user_id}:{key}".encode()).hexdigest()


async def lock_attempt(session: AsyncSession, key: str, game: str) -> None:
    digest = hashlib.sha256(f"purchase:{game}:{key}".encode()).digest()
    lock_id = int.from_bytes(digest[:8], "big", signed=True)
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id}
    )


async def guard_attempt(
    session: AsyncSession, user_id: UUID, key: str, game: str
) -> None:
    # Older clients/bots keep their existing keys and behavior.
    if not key.startswith("m1-"):
        return
    await lock_attempt(session, key, game)
    cancelled = await session.scalar(
        select(PurchaseCancellation.id).where(
            PurchaseCancellation.user_id == user_id,
            PurchaseCancellation.game == game,
            PurchaseCancellation.key == key,
        )
    )
    if cancelled is not None:
        raise InvalidTicket("This uncommitted purchase attempt was cancelled.")
