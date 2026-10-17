"""Kasper LIVE fixed-odds and atomic accounting tests."""

from collections import Counter
from collections.abc import Iterable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.instant import InstantTicketPurchaseService
from k_loto.application.weekly import KASPER_FUND_ID
from k_loto.domain.enums import LedgerAccountKind, TransactionType
from k_loto.domain.instant import (
    PRIZE_BANDS,
    TICKET_PRICE,
    instant_rules,
    instant_rules_for_version,
    instant_versions,
    prize_for_roll,
    symbols_for_prize,
)
from k_loto.infrastructure.database.models import (
    Balance,
    InstantTicket,
    KasperFundAccount,
    LedgerTransaction,
)


class TransactionContext(AbstractAsyncContextManager[object]):
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeSession:
    def __init__(self, values: Iterable[Any]) -> None:
        self.values = iter(values)
        self.added: list[Any] = []

    def begin(self) -> TransactionContext:
        return TransactionContext()

    async def scalar(self, _statement: object) -> Any:
        return next(self.values)

    def add_all(self, values: Iterable[Any]) -> None:
        self.added.extend(values)

    async def flush(self) -> None:
        number = 1_000
        for item in self.added:
            if isinstance(item, InstantTicket) and item.public_number is None:
                item.public_number = number
                number += 1


class FixedGenerator:
    def __init__(self) -> None:
        self.values = iter(((1,), (7_001,), (10_000,), (1, 2, 3), (4, 5, 6), (7, 8, 1)))

    def draw(self, _population_size: int, _numbers_to_pick: int) -> tuple[int, ...]:
        raise AssertionError("Kasper LIVE uses sequence draws.")

    def draw_sequence(
        self, _minimum: int, _maximum: int, _length: int
    ) -> tuple[int, ...]:
        return next(self.values)


@pytest.mark.parametrize(
    ("roll", "expected"),
    (
        (1, 0),
        (6_000, 0),
        (6_001, 1_000),
        (7_500, 1_000),
        (7_501, 2_000),
        (9_300, 2_000),
        (9_301, 5_000),
        (9_800, 5_000),
        (9_801, 20_000),
        (9_980, 20_000),
        (9_981, 100_000),
        (9_999, 100_000),
        (10_000, 1_000_000),
    ),
)
def test_prize_band_boundaries(roll: int, expected: int) -> None:
    assert prize_for_roll(roll) == expected


def test_prize_table_is_complete_and_has_agreed_rtp() -> None:
    assert Counter(prize_for_roll(roll) for roll in range(1, 10_001)) == {
        0: 6000,
        1000: 1500,
        2000: 1800,
        5000: 500,
        20000: 180,
        100000: 19,
        1000000: 1,
    }
    lower = 1
    expected_payout = 0
    for band in PRIZE_BANDS:
        expected_payout += (band.upper_roll - lower + 1) * band.prize
        lower = band.upper_roll + 1

    assert lower == 10_001
    assert expected_payout / 10_000 == 1_410
    assert expected_payout / 10_000 / TICKET_PRICE == pytest.approx(0.705)


def test_live_new_odds_keep_the_original_version_resolvable() -> None:
    current = instant_rules("kasper-live")
    old = instant_rules_for_version("kasper-live-v1")
    assert current.version == "kasper-live-v2" and current.price == old.price == 2000
    assert current.prize(8000) == 2000 and old.prize(8000) == 1000
    assert instant_versions("kasper-live") == ("kasper-live-v1", "kasper-live-v2")
    assert instant_versions("vault") == ("casper-vault-v1",)


@pytest.mark.parametrize("roll", (0, 10_001))
def test_prize_roll_rejects_values_outside_distribution(roll: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 10,000"):
        prize_for_roll(roll)


@pytest.mark.asyncio
async def test_three_ticket_purchase_burns_price_and_ledgers_prize() -> None:
    user_id = UUID("00000000-0000-0000-0000-000000000111")
    balance = Balance(user_id=user_id, amount=10_000, version=1)
    fund = KasperFundAccount(id=KASPER_FUND_ID, balance=3_000_000, version=1)
    fake = FakeSession((None, fund, balance, None))

    result = await InstantTicketPurchaseService(
        cast(AsyncSession, fake), FixedGenerator()
    ).purchase(
        user_id=user_id,
        quantity=3,
        idempotency_key="batch-three",
        now=datetime(2026, 9, 22, 1, tzinfo=UTC),
    )

    assert result.total_cost == 6_000
    assert result.total_prize == 1_001_000
    assert result.balance_after == 1_005_000
    assert [ticket.prize_amount for ticket in result.tickets] == [0, 1_000, 1_000_000]
    assert [ticket.symbols for ticket in result.tickets] == [
        (1, 2, 3),
        (2, 2, 2),
        (7, 7, 7),
    ]
    assert balance.amount == 1_005_000
    assert fund.balance == 1_999_000

    ledger = [item for item in fake.added if isinstance(item, LedgerTransaction)]
    assert len(ledger) == 3
    assert [(item.account_kind, item.type, item.amount) for item in ledger] == [
        (LedgerAccountKind.USER_BALANCE, TransactionType.TICKET_PURCHASE, -6_000),
        (LedgerAccountKind.KASPER_FUND, TransactionType.PRIZE_PAYOUT, -1_001_000),
        (LedgerAccountKind.USER_BALANCE, TransactionType.PRIZE_PAYOUT, 1_001_000),
    ]
    assert not any(
        item.account_kind == LedgerAccountKind.KASPER_FUND
        and item.type == TransactionType.TICKET_PURCHASE
        for item in ledger
    )


@pytest.mark.parametrize("prize", (0, 1_000, 2_000, 5_000, 20_000, 100_000, 1_000_000))
def test_symbols_identify_prize_category(prize: int) -> None:
    symbols = symbols_for_prize(prize)
    assert len(symbols) == 3
    if prize == 0:
        assert len(set(symbols)) == 3
    else:
        assert symbols[0] == symbols[1] == symbols[2]
