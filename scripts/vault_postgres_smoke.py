"""Exercise instant pricing and historical LIVE reads on a disposable database."""

import asyncio
import json
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import func, select, text

from k_loto.application.admin import AdminQueryService
from k_loto.application.instant import (
    InstantTicketPurchaseService,
    InstantTicketQueryService,
)
from k_loto.application.miniapp import MiniAppQueryService
from k_loto.application.weekly import _ledger_entry
from k_loto.domain.enums import LedgerAccountKind, TransactionType
from k_loto.domain.errors import InvalidTicket
from k_loto.domain.instant import LEGACY_LIVE_RULES
from k_loto.infrastructure.database.models import Balance, InstantTicket, User
from k_loto.infrastructure.database.session import engine, session_factory


class Fixed:
    def __init__(self):
        self.rolls = iter((2200, 9900, 10000))

    def draw_sequence(self, *_args):
        return (next(self.rolls),)

    def draw(self, *_args):
        raise AssertionError("Instant games draw a uniform roll.")


async def main():
    database = engine.url.database or ""
    if database != "k_loto_vault_smoke" and not database.startswith(
        "k_loto_audit_stage1_"
    ):
        raise RuntimeError("Only the disposable Vault smoke database is allowed.")
    uid = uuid4()
    async with session_factory() as s:
        live_before = await InstantTicketQueryService(s).summary()
    async with session_factory() as s, s.begin():
        before = await s.scalar(
            text(
                "SELECT md5(coalesce(string_agg(row_to_json(t)::text, '' "
                "ORDER BY id), '')) FROM instant_tickets t"
            )
        )
        s.add(User(id=uid, display_name="Disposable Vault smoke", is_active=True))
        await s.flush()
        s.add(Balance(user_id=uid, amount=100000, version=1))
        s.add(
            _ledger_entry(
                operation_id=uuid4(),
                idempotency_key=f"smoke-seed-{uid}",
                account_kind=LedgerAccountKind.USER_BALANCE,
                account_id=uid,
                transaction_type=TransactionType.SYSTEM_ADJUSTMENT,
                before=0,
                after=100000,
                user_id=uid,
                details={"reason": "Disposable smoke seed"},
            )
        )

    async def buy():
        async with session_factory() as s:
            return await InstantTicketPurchaseService(
                s, Fixed(), game_code="vault"
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
            == 100000
        )
        assert (
            await s.scalar(
                select(func.count(InstantTicket.id)).where(InstantTicket.user_id == uid)
            )
            == 0
        )
    results = await asyncio.gather(buy(), buy())
    assert sum(r.already_processed for r in results) == 1
    assert all(r.total_cost == 90000 and r.total_prize == 6003000 for r in results)
    assert results[0].tickets == results[1].tickets
    async with session_factory() as s:
        live = await InstantTicketPurchaseService(s, Fixed()).purchase(
            user_id=uid, quantity=1, idempotency_key=f"smoke-{uid}"
        )
        assert live.total_cost == 2000 and live.total_prize == 0
    async with session_factory() as s:
        with patch(
            "k_loto.application.instant.instant_rules", return_value=LEGACY_LIVE_RULES
        ):
            old_live_service = InstantTicketPurchaseService(s, Fixed())
        old_live = await old_live_service.purchase(
            user_id=uid, quantity=1, idempotency_key=f"legacy-live-{uid}"
        )
        assert old_live.total_cost == 2000 and old_live.total_prize == 0
    async with session_factory() as s:
        aurora = await InstantTicketPurchaseService(
            s, Fixed(), game_code="aurora"
        ).purchase(user_id=uid, quantity=1, idempotency_key=f"smoke-{uid}")
        assert aurora.total_cost == 3000 and aurora.total_prize == 0
    async with session_factory() as s:
        assert (
            len(await InstantTicketQueryService(s).history(uid, game_code="vault")) == 3
        )
        assert len(await InstantTicketQueryService(s).history(uid)) == 2
        live_after = await InstantTicketQueryService(s).summary()
        assert live_after.ticket_count == live_before.ticket_count + 2
        assert live_after.result == live_before.result + 4000
        miniapp = MiniAppQueryService(s)
        assert (
            await miniapp.ticket_count(uid, active=False, lottery_code="kasper-live")
            == 2
        )
        assert (
            len(await miniapp.tickets(uid, active=False, lottery_code="kasper-live"))
            == 2
        )
        page, cursor, more = await miniapp.history_page(uid, lottery_code="kasper-live")
        assert len(page) == 2 and not cursor and not more
        assert all(t.lottery_code == "kasper-live" for t in page)
        rows, total, stats = await AdminQueryService(s).player_ticket_history(
            uid, lottery_code="kasper-live"
        )
        assert total == len(rows) == 2
        assert all(t.lottery_code == "kasper-live" for t in rows)
        live_stats = next(stat for stat in stats if stat.lottery_code == "kasper-live")
        assert live_stats.ticket_count == 2
        assert (
            await s.scalar(select(Balance.amount).where(Balance.user_id == uid))
            == 6006000
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
            "TICKET_PURCHASE": -97000,
            "PRIZE_PAYOUT": 0,
            "SYSTEM_ADJUSTMENT": 100000,
        }
    async with session_factory() as s:
        try:
            await InstantTicketPurchaseService(s, game_code="vault").purchase(
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
