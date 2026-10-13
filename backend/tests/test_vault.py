"""Vault exact odds, ledger settlement and instant-game isolation."""

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
from k_loto.domain.instant import LIVE_RULES, VAULT_RULES
from k_loto.infrastructure.database.models import (
    Balance,
    InstantTicket,
    KasperFundAccount,
    LedgerTransaction,
)
from test_instant import FakeSession, FixedGenerator


class VaultGenerator(FixedGenerator):
    def __init__(self):
        self.values = iter(((2200,), (9900,), (10000,)))


def test_vault_full_distribution_and_live_unchanged() -> None:
    counts = Counter(VAULT_RULES.prize(roll) for roll in range(1, 10_001))
    assert counts == {
        0: 2199,
        3000: 3500,
        5000: 2500,
        10000: 1000,
        50000: 500,
        300000: 200,
        1000000: 100,
        5000000: 1,
    }
    assert sum(prize * count for prize, count in counts.items()) == 223_000_000
    assert VAULT_RULES.price == 5000
    assert LIVE_RULES.price == 2000 and LIVE_RULES.prize(7001) == 1000
    assert len({VAULT_RULES.symbols(prize) for prize in counts}) == 8


@pytest.mark.parametrize("roll", [0, 10001])
def test_vault_rejects_invalid_random_roll(roll: int) -> None:
    with pytest.raises(ValueError):
        VAULT_RULES.prize(roll)


@pytest.mark.asyncio
async def test_vault_three_settles_and_replays_without_new_draw_or_money() -> None:
    user = UUID(int=111)
    balance = Balance(user_id=user, amount=20000, version=1)
    fund = KasperFundAccount(id=KASPER_FUND_ID, balance=15000000, version=1)
    fake = FakeSession((None, fund, balance, None))
    result = await InstantTicketPurchaseService(
        cast(AsyncSession, fake), VaultGenerator(), game_code="vault"
    ).purchase(user_id=user, quantity=3, idempotency_key="same")
    assert result.total_cost == 15000 and result.total_prize == 6003000
    assert balance.amount == 6008000 and fund.balance == 8997000
    tickets = [t for t in fake.added if isinstance(t, InstantTicket)]
    assert all(
        t.odds_version == VAULT_RULES.version and t.purchase_price == 5000
        for t in tickets
    )
    entries = [t for t in fake.added if isinstance(t, LedgerTransaction)]
    assert [t.amount for t in entries] == [-15000, -6003000, 6003000]
    assert entries[0].idempotency_key == "instant-vault:same:user:purchase"

    class ReplaySession(FakeSession):
        async def scalars(self, _statement):
            class Rows:
                def all(self):
                    return tickets

            return Rows()

    replay = ReplaySession((entries[0],))
    again = await InstantTicketPurchaseService(
        cast(AsyncSession, replay), game_code="vault"
    ).purchase(user_id=user, quantity=3, idempotency_key="same")
    assert again.already_processed and again.tickets == result.tickets
    assert again.balance_after == result.balance_after
    assert not replay.added
    for wrong_user, qty in [(UUID(int=222), 3), (user, 1)]:
        with pytest.raises(InvalidTicket):
            await InstantTicketPurchaseService(
                cast(AsyncSession, FakeSession((entries[0],))), game_code="vault"
            ).purchase(user_id=wrong_user, quantity=qty, idempotency_key="same")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "amount,fund_amount,error",
    [(4999, 10000000, InsufficientBalance), (5000, 4999999, ConfigurationError)],
)
async def test_vault_rejection_has_no_ticket_or_ledger(
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
            cast(AsyncSession, fake), Winner(), game_code="vault"
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
            assert "casper-vault-v1" in sql and "user_id" in sql

            class Rows:
                def all(self):
                    return []

            return Rows()

    assert (
        await InstantTicketQueryService(cast(AsyncSession, QuerySession())).history(
            UUID(int=111), game_code="vault"
        )
        == ()
    )
