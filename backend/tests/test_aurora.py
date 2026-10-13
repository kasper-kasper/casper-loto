"""Aurora exact odds, ledger settlement and instant-game isolation."""

from collections import Counter
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.instant import (
    InstantTicketPurchaseService,
    InstantTicketQueryService,
)
from k_loto.application.weekly import KASPER_FUND_ID
from k_loto.domain.errors import ConfigurationError, InsufficientBalance, InvalidTicket
from k_loto.domain.instant import AURORA_RULES, LIVE_RULES
from k_loto.infrastructure.database.models import (
    Balance,
    InstantTicket,
    KasperFundAccount,
    LedgerTransaction,
)
from test_instant import FakeSession, FixedGenerator


def test_aurora_full_distribution_and_live_unchanged() -> None:
    counts = Counter(AURORA_RULES.prize(roll) for roll in range(1, 10_001))
    assert counts == {
        0: 6000,
        2000: 2000,
        3000: 1000,
        6000: 700,
        25000: 280,
        200000: 19,
        1000000: 1,
    }
    assert sum(prize * count for prize, count in counts.items()) == 23_000_000
    assert AURORA_RULES.price == 3000
    assert LIVE_RULES.price == 2000 and LIVE_RULES.prize(7001) == 1000
    assert len({AURORA_RULES.symbols(prize) for prize in counts}) == 7


@pytest.mark.parametrize("roll", [0, 10001])
def test_aurora_rejects_invalid_random_roll(roll: int) -> None:
    with pytest.raises(ValueError):
        AURORA_RULES.prize(roll)


@pytest.mark.asyncio
async def test_aurora_three_settles_and_replays_without_new_draw_or_money() -> None:
    user = UUID(int=111)
    balance = Balance(user_id=user, amount=10000, version=1)
    fund = KasperFundAccount(id=KASPER_FUND_ID, balance=3000000, version=1)
    fake = FakeSession((None, fund, balance, None))
    result = await InstantTicketPurchaseService(
        cast(AsyncSession, fake), FixedGenerator(), game_code="aurora"
    ).purchase(user_id=user, quantity=3, idempotency_key="same")
    assert result.total_cost == 9000 and result.total_prize == 1002000
    assert balance.amount == 1003000 and fund.balance == 1998000
    tickets = [t for t in fake.added if isinstance(t, InstantTicket)]
    assert all(
        t.odds_version == AURORA_RULES.version and t.purchase_price == 3000
        for t in tickets
    )
    entries = [t for t in fake.added if isinstance(t, LedgerTransaction)]
    assert [t.amount for t in entries] == [-9000, -1002000, 1002000]
    assert entries[0].idempotency_key == "instant-aurora:same:user:purchase"

    class ReplaySession(FakeSession):
        async def scalars(self, _statement):
            class Rows:
                def all(self):
                    return tickets

            return Rows()

    replay = ReplaySession((entries[0],))
    again = await InstantTicketPurchaseService(
        cast(AsyncSession, replay), game_code="aurora"
    ).purchase(user_id=user, quantity=3, idempotency_key="same")
    assert again.already_processed and again.tickets == result.tickets
    assert again.balance_after == result.balance_after
    assert not replay.added
    for wrong_user, qty in [(UUID(int=222), 3), (user, 1)]:
        with pytest.raises(InvalidTicket):
            await InstantTicketPurchaseService(
                cast(AsyncSession, FakeSession((entries[0],))), game_code="aurora"
            ).purchase(user_id=wrong_user, quantity=qty, idempotency_key="same")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "amount,fund_amount,error",
    [(2999, 2000000, InsufficientBalance), (3000, 0, ConfigurationError)],
)
async def test_aurora_rejection_has_no_ticket_or_ledger(
    amount, fund_amount, error
) -> None:
    class Winner(FixedGenerator):
        def draw_sequence(self, *_args):
            return (10000,)

    user = UUID(int=111)
    fake = FakeSession(
        (
            None,
            KasperFundAccount(id=KASPER_FUND_ID, balance=fund_amount, version=1),
            Balance(user_id=user, amount=amount, version=1),
            None,
        )
    )
    with pytest.raises(error):
        await InstantTicketPurchaseService(
            cast(AsyncSession, fake), Winner(), game_code="aurora"
        ).purchase(user_id=user, quantity=1, idempotency_key="fail")
    assert not fake.added


@pytest.mark.asyncio
async def test_history_query_is_scoped_to_game_and_owner() -> None:
    from sqlalchemy.dialects import postgresql

    class QuerySession:
        async def scalars(self, statement):
            sql = str(
                statement.compile(
                    dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
                )
            )
            assert "casper-aurora-v1" in sql and "user_id" in sql

            class Rows:
                def all(self):
                    return []

            return Rows()

    assert (
        await InstantTicketQueryService(cast(AsyncSession, QuerySession())).history(
            UUID(int=111), game_code="aurora"
        )
        == ()
    )
