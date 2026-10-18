"""PostgreSQL recovery regressions; refused outside a disposable audit database."""

import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select

from k_loto.application.instant import InstantTicketPurchaseService
from k_loto.application.purchase_receipts import PurchaseReceiptService
from k_loto.application.weekly import LotteryTicketPurchaseService
from k_loto.core.config import get_settings
from k_loto.domain.enums import DrawStatus
from k_loto.domain.errors import InvalidTicket
from k_loto.domain.lottery_rules import CLASSIC_6_36_RULES, CLASSIC_ECONOMY_RULES
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    LedgerTransaction,
    Lottery,
    PurchaseCancellation,
)
from k_loto.infrastructure.database.session import engine, session_factory


class LosingRoll:
    def draw_sequence(
        self, _minimum: int, _maximum: int, _length: int
    ) -> tuple[int, ...]:
        return (1,)


async def main() -> None:
    database = get_settings().database_url.path or ""
    if not database.lstrip("/").startswith("kloto_recovery_check_"):
        raise RuntimeError("Recovery checks require a disposable audit database.")
    async with engine.begin() as connection:
        # Only the additive fence table is needed in this restored database.
        await connection.run_sync(
            lambda sync: PurchaseCancellation.__table__.create(sync, checkfirst=True)
        )
    async with session_factory() as session:
        lottery = await session.scalar(
            select(Lottery).where(
                Lottery.ruleset_code.in_(
                    (CLASSIC_6_36_RULES.code, CLASSIC_ECONOMY_RULES.code)
                ),
                Lottery.is_active.is_(True),
            )
        )
        assert lottery is not None
        lottery_code = lottery.code
        user = await session.scalar(
            select(Balance.user_id).order_by(Balance.amount.desc()).limit(1)
        )
        assert user is not None
        draw = await session.scalar(
            select(Draw)
            .where(
                Draw.lottery_id == lottery.id,
                Draw.status == DrawStatus.SCHEDULED,
                Draw.sales_close_at > datetime.now(UTC),
            )
            .order_by(Draw.scheduled_at)
            .limit(1)
        )
        assert draw is not None
        scheduled = draw.scheduled_at
        combinations = [list(range(1, lottery.numbers_to_pick + 1))] * 25

    async def purchase(key: str):
        async with session_factory() as session:
            return await LotteryTicketPurchaseService(
                session, lottery_code=lottery_code
            ).purchase(
                user_id=user,
                combinations=combinations,
                idempotency_key=key,
                expected_scheduled_at=scheduled,
            )

    key = "m1-check-" + uuid4().hex
    first, second = await asyncio.gather(purchase(key), purchase(key))
    assert first.operation_id == second.operation_id
    assert first.ticket_ids == second.ticket_ids and len(first.ticket_ids) == 25
    assert first.already_processed != second.already_processed
    async with session_factory() as session:
        assert (
            await session.scalar(
                select(func.count(LedgerTransaction.id)).where(
                    LedgerTransaction.idempotency_key == f"purchase:{key}:user",
                )
            )
            == 1
        )
        recovered = await PurchaseReceiptService(session).find(user, key, "scheduled")
        assert recovered is not None and recovered.operation_id == first.operation_id
        assert (
            await PurchaseReceiptService(session).find(uuid4(), key, "scheduled")
            is None
        )
    async with session_factory() as session:
        confirmed = await PurchaseReceiptService(session).cancel_uncommitted(
            user, key, "scheduled"
        )
        assert confirmed is not None and confirmed.operation_id == first.operation_id
    cancelled_key = "m1-cancel-" + uuid4().hex
    async with session_factory() as session:
        assert (
            await PurchaseReceiptService(session).cancel_uncommitted(
                user, cancelled_key, "scheduled"
            )
            is None
        )
    try:
        await purchase(cancelled_key)
    except InvalidTicket:
        pass
    else:
        raise AssertionError("A late request bypassed its cancellation fence.")
    for _ in range(4):
        race_key = "m1-race-" + uuid4().hex

        async def cancel(key: str = race_key):
            async with session_factory() as session:
                return await PurchaseReceiptService(session).cancel_uncommitted(
                    user, key, "scheduled"
                )

        bought, cancelled = await asyncio.gather(
            purchase(race_key), cancel(), return_exceptions=True
        )
        if isinstance(bought, InvalidTicket):
            assert cancelled is None
        else:
            assert not isinstance(bought, BaseException)
            assert cancelled is not None and not isinstance(cancelled, BaseException)
            assert bought.operation_id == cancelled.operation_id
    for game in ("kasper-live", "aurora", "vault"):
        instant_key = "m1-instant-" + uuid4().hex
        async with session_factory() as session:
            result = await InstantTicketPurchaseService(
                session, LosingRoll(), game_code=game
            ).purchase(
                user_id=user,
                quantity=3,
                idempotency_key=instant_key,
            )
        async with session_factory() as session:
            recovered_instant = await PurchaseReceiptService(session).find(
                user, instant_key, game
            )
            assert (
                recovered_instant is not None
                and recovered_instant.operation_id == result.operation_id
            )
            assert len(recovered_instant.tickets) == 3
    print(
        json.dumps(
            {
                "concurrent_x25": "single_purchase",
                "foreign_receipt": "hidden",
                "committed_cancel": "receipt_returned",
                "late_cancelled_request": "rejected",
                "purchase_cancel_races": 4,
                "instant_receipts": 3,
                "database_scope": "disposable_only",
            }
        )
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
