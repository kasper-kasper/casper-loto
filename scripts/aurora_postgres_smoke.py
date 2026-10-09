"""Exercise Aurora accounting on an isolated PostgreSQL backup clone only."""

import asyncio
import json
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import func, select, text

from k_loto.application.instant import (
    InstantTicketPurchaseService,
    InstantTicketQueryService,
)
from k_loto.application.weekly import _ledger_entry
from k_loto.core.config import get_settings
from k_loto.domain.enums import LedgerAccountKind, TransactionType
from k_loto.domain.errors import InvalidTicket
from k_loto.infrastructure.database.models import Balance, InstantTicket, User
from k_loto.infrastructure.database.session import engine, session_factory


class Fixed:
    def __init__(self):
        self.rolls = iter((6001, 9001, 10000))

    def draw_sequence(self, *_args):
        return (next(self.rolls),)

    def draw(self, *_args):
        raise AssertionError("Instant games draw a uniform roll.")


async def main():
    if (
        not str(get_settings().database_url)
        .rstrip("/")
        .endswith("/k_loto_aurora_smoke")
    ):
        raise RuntimeError("Only the disposable Aurora smoke database is allowed.")
    uid = uuid4()
    async with session_factory() as s, s.begin():
        before = await s.scalar(
            text(
                "SELECT md5(coalesce(string_agg(row_to_json(t)::text, '' "
                "ORDER BY id), '')) FROM instant_tickets t"
            )
        )
        s.add(User(id=uid, display_name="Disposable Aurora smoke", is_active=True))
        await s.flush()
        s.add(Balance(user_id=uid, amount=10000, version=1))
        s.add(
            _ledger_entry(
                operation_id=uuid4(),
                idempotency_key=f"smoke-seed-{uid}",
                account_kind=LedgerAccountKind.USER_BALANCE,
                account_id=uid,
                transaction_type=TransactionType.SYSTEM_ADJUSTMENT,
                before=0,
                after=10000,
                user_id=uid,
                details={"reason": "Disposable smoke seed"},
            )
        )

    async def buy():
        async with session_factory() as s:
            return await InstantTicketPurchaseService(
                s, Fixed(), game_code="aurora"
            ).purchase(user_id=uid, quantity=3, idempotency_key=f"smoke-{uid}")

    with patch(
        "k_loto.application.instant._ledger_entry", side_effect=RuntimeError("rollback")
    ):
        try:
            await buy()
        except RuntimeError as e:
            assert str(e) == "rollback"
        else:
            raise AssertionError("Rollback injection did not fail.")
    async with session_factory() as s:
        assert (
            await s.scalar(select(Balance.amount).where(Balance.user_id == uid))
            == 10000
        )
        assert (
            await s.scalar(
                select(func.count(InstantTicket.id)).where(InstantTicket.user_id == uid)
            )
            == 0
        )
    results = await asyncio.gather(buy(), buy())
    assert sum(r.already_processed for r in results) == 1
    assert all(r.total_cost == 9000 and r.total_prize == 1008000 for r in results)
    assert results[0].tickets == results[1].tickets
    async with session_factory() as s:
        live = await InstantTicketPurchaseService(s, Fixed()).purchase(
            user_id=uid, quantity=1, idempotency_key=f"smoke-{uid}"
        )
        assert live.total_cost == 2000 and live.total_prize == 0
    async with session_factory() as s:
        assert (
            len(await InstantTicketQueryService(s).history(uid, game_code="aurora"))
            == 3
        )
        assert len(await InstantTicketQueryService(s).history(uid)) == 1
        assert (
            await s.scalar(select(Balance.amount).where(Balance.user_id == uid))
            == 1007000
        )
        after = await s.scalar(
            text(
                "SELECT md5(coalesce(string_agg(row_to_json(t)::text, '' "
                "ORDER BY id), '')) FROM instant_tickets t WHERE user_id <> :uid"
            ),
            {"uid": uid},
        )
        assert before == after
        amounts = (
            await s.execute(
                text(
                    "SELECT type::text,sum(amount) FROM ledger_transactions "
                    "WHERE user_id=:uid GROUP BY type"
                ),
                {"uid": uid},
            )
        ).all()
        assert dict(amounts) == {
            "TICKET_PURCHASE": -11000,
            "PRIZE_PAYOUT": 0,
            "SYSTEM_ADJUSTMENT": 10000,
        }
    async with session_factory() as s:
        try:
            await InstantTicketPurchaseService(s, game_code="aurora").purchase(
                user_id=uid, quantity=1, idempotency_key=f"smoke-{uid}"
            )
        except InvalidTicket:
            pass
        else:
            raise AssertionError("Changed quantity must not replay another request.")
    print(
        json.dumps(
            {
                "rollback": True,
                "concurrent_idempotency": True,
                "game_history_isolation": True,
                "existing_history_preserved": True,
                "ledger_settlement": True,
            }
        )
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
