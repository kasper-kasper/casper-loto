"""Read-only recovery of committed purchases from the immutable ledger."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.instant import (
    InstantPurchaseResult,
    InstantTicketPurchaseService,
)
from k_loto.application.purchase_guard import bingo_purchase_key, lock_attempt
from k_loto.application.weekly import PurchaseResult, _existing_purchase_result
from k_loto.infrastructure.database.models import (
    LedgerTransaction,
    PurchaseCancellation,
)


class PurchaseReceiptService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(
        self, user_id: UUID, key: str, game: str
    ) -> PurchaseResult | InstantPurchaseResult | None:
        instant = game in {"kasper-live", "aurora", "vault"}
        namespace = "instant" if game == "kasper-live" else f"instant-{game}"
        ledger_key = (
            f"{namespace}:{key}:user:purchase" if instant else f"purchase:{key}:user"
        )
        ledger_keys = [ledger_key]
        if not instant:
            ledger_keys.append(f"purchase:{bingo_purchase_key(user_id, key)}:user")
        ledger = await self._session.scalar(
            select(LedgerTransaction).where(
                LedgerTransaction.idempotency_key.in_(ledger_keys),
                LedgerTransaction.user_id == user_id,
                LedgerTransaction.account_id == user_id,
            )
        )
        if ledger is None:
            return None
        if instant:
            return await InstantTicketPurchaseService(
                self._session, game_code=game
            )._existing_result(ledger)
        return _existing_purchase_result(ledger, user_id)

    async def cancel_uncommitted(
        self, user_id: UUID, key: str, game: str
    ) -> PurchaseResult | InstantPurchaseResult | None:
        if not key.startswith("m1-") or len(key) > 100:
            raise ValueError("Only durable Mini App requests can be cancelled.")
        async with self._session.begin():
            await lock_attempt(self._session, key, game)
            receipt = await self.find(user_id, key, game)
            if receipt is not None:
                return receipt
            exists = await self._session.scalar(
                select(PurchaseCancellation.id).where(
                    PurchaseCancellation.user_id == user_id,
                    PurchaseCancellation.game == game,
                    PurchaseCancellation.key == key,
                )
            )
            if exists is None:
                self._session.add(
                    PurchaseCancellation(
                        id=uuid4(), user_id=user_id, game=game, key=key
                    )
                )
        return None
