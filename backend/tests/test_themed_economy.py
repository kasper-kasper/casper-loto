"""Exact thematic amounts, per-ticket rounding and paused batch application."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.economy_transition import STEP as PAUSE_STEP
from k_loto.application.themed_economy import STEP, TERMS, ThemedEconomyService
from k_loto.application.weekly import LotteryTicketPurchaseService
from k_loto.domain.enums import LedgerAccountKind
from k_loto.domain.errors import (
    ConfigurationError,
    InvalidStateTransition,
    InvalidTicket,
)
from k_loto.domain.lottery_rules import (
    DAILY_RULES,
    FAST_RULES,
    HALLOWEEN_RULES,
    SEPTEMBER_RULES,
    PayoutRatio,
    SettlementTicket,
    get_lottery_rules,
)
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    KasperFundAccount,
    LedgerTransaction,
    Ticket,
)
from test_weekly_application import FakeSession, build_purchase_accounts


@pytest.mark.parametrize("code,rule,price,base", TERMS)
def test_exact_splits_and_all_payout_categories(code, rule, price, base):
    contribution = {"pll": 11_111, "grob": 3_333, "september": 1_667}[code]
    numbers = list(range(1, rule.numbers_to_pick + 1))
    for count in (1, 25, 100):
        quote = rule.quote_purchase([numbers] * count, price, price * count)
        assert quote.jackpot_contribution == contribution * count
        assert quote.distribution_contribution == (price - contribution) * count
    expected = {
        "pll": [0, 0, 22_222, 44_444, base + 7],
        "grob": [0, 0, 66_666, base + 7],
        "september": [0, 3_333, 9_999, base + 7],
    }[code]
    for matches, amount in enumerate(expected):
        ticket = SettlementTicket(
            uuid4(),
            1,
            uuid4(),
            (*range(1, matches + 1), *range(10, 10 + len(numbers) - matches)),
            price,
        )
        plan = rule.calculate_settlement(
            [ticket],
            numbers,
            distribution_balance=0,
            jackpot_balance=base + 7,
            reserve_balance=100_000_000,
            base_jackpot=base,
        )
        assert plan.payouts[0].amount == amount
    assert get_lottery_rules(rule.code) is rule


def test_half_split_uses_integer_arithmetic_without_changing_legacy_payout_rounding():
    rule = TERMS[2][1]
    assert rule.jackpot_contribution(2**60 + 1) == 2**59 + 1
    assert (
        replace(rule, jackpot_share=PayoutRatio(50, 100)).jackpot_contribution(3333)
        == 1667
    )
    assert PayoutRatio(1, 2).apply(3333) == 1666
    assert FAST_RULES.jackpot_contribution(2000) == 800
    for old, new in zip(
        (DAILY_RULES, HALLOWEEN_RULES, SEPTEMBER_RULES), TERMS, strict=True
    ):
        assert get_lottery_rules(old.code) is old
        assert old.jackpot_contribution(3334) == 3334
        assert (old.numbers_to_pick, old.max_number) == (
            new[1].numbers_to_pick,
            new[1].max_number,
        )
    assert DAILY_RULES.guaranteed_payouts[3].apply(22_222) == 66_666
    assert HALLOWEEN_RULES.fixed_payouts[2] == 28_000
    assert SEPTEMBER_RULES.fixed_payouts[1] == 333


@pytest.mark.parametrize(
    "draw_count,count,existing", [(1, 25, 0), (5, 25, 0), (1, 1, 99), (1, 1, 100)]
)
async def test_real_purchase_ledger_rounds_every_ticket_and_enforces_cumulative_cap(
    draw_count, count, existing
):
    now = datetime(2026, 10, 18, tzinfo=UTC)
    user, lottery, draw, balance, jackpot, _ = build_purchase_accounts(now)
    rule = TERMS[2][1]
    lottery.code = "september"
    lottery.ruleset_code = rule.code
    lottery.numbers_to_pick = 3
    lottery.max_number = 33
    lottery.ticket_price = 3333
    lottery.max_tickets_per_purchase = 100
    lottery.max_tickets_per_user_per_draw = 100
    balance.amount = 1_000_000
    initial_jackpot = jackpot.balance
    if draw_count == 1:
        values = [None, lottery, jackpot, None, draw, existing, balance]
        collections = []
    else:
        values = [
            None,
            lottery,
            jackpot,
            None,
            draw,
            *([existing] * draw_count),
            balance,
        ]
        collections = [[draw]]
    fake = FakeSession(scalar_values=values, scalar_collections=collections)
    service = LotteryTicketPurchaseService(
        cast(AsyncSession, fake), lottery_code="september"
    )
    kwargs = dict(
        user_id=user,
        combinations=[[1, 2, 3]] * count,
        idempotency_key="themed",
        now=now,
        draw_count=draw_count,
    )
    if existing + count > 100:
        with pytest.raises(InvalidTicket, match="per-player ticket limit"):
            await service.purchase(**kwargs)
        assert not fake.added
        assert balance.amount == 1_000_000
        return
    await service.purchase(**kwargs)
    total = count * draw_count
    ledger = [x for x in fake.added if isinstance(x, LedgerTransaction)]
    assert jackpot.balance - initial_jackpot == total * 1667
    assert balance.amount == 1_000_000 - total * 3333
    assert sum(x.amount for x in ledger) == -total * 1666
    assert ledger[0].details["burned_cas"] == total * 1666
    assert len([x for x in fake.added if isinstance(x, Ticket)]) == total


class BatchSession(FakeSession):
    async def execute(self, statement, params):
        assert "pg_advisory_xact_lock" in str(statement)


def batch_objects(terms=TERMS):
    now = datetime(2026, 10, 18, tzinfo=UTC)
    control = SimpleNamespace(
        paused=True,
        epoch=2,
        applied_steps={PAUSE_STEP: {}},
        pause_started_at=now,
        recovery_after=None,
    )
    lotteries, jackpots = [], []
    for code, rule, _, base in terms:
        _, lottery, _, _, jackpot, _ = build_purchase_accounts(now)
        lottery.id = uuid4()
        lottery.code = code
        lottery.ruleset_code = "old"
        lottery.numbers_to_pick = rule.numbers_to_pick
        lottery.max_number = rule.max_number
        jackpot.id = uuid4()
        jackpot.lottery_id = lottery.id
        jackpot.balance = base + (1000 if code == "grob" else -1000)
        lotteries.append(lottery)
        jackpots.append(jackpot)
    fund = KasperFundAccount(id=uuid4(), balance=100_000_000, version=1)
    return control, lotteries, jackpots, fund


async def test_batch_preserves_history_balances_ledger_and_is_repeatable():
    control, lotteries, jackpots, fund = batch_objects()
    counters = [
        (x.next_draw_number, x.next_ticket_number, dict(x.schedule)) for x in lotteries
    ]
    initial_total = fund.balance + sum(x.balance for x in jackpots)
    fake = BatchSession(
        scalar_values=[object(), control, None, None, fund],
        scalar_collections=[lotteries, jackpots],
    )
    owner = uuid4()
    await ThemedEconomyService(cast(AsyncSession, fake)).apply(owner_id=owner)
    for lottery, jackpot, (_, rule, price, base) in zip(
        lotteries, jackpots, TERMS, strict=True
    ):
        assert (lottery.ticket_price, lottery.ruleset_code) == (price, rule.code)
        assert lottery.max_tickets_per_user_per_draw == 100
        assert lottery.max_tickets_per_purchase == 100
        assert jackpot.balance == jackpot.base_amount == base
    assert counters == [
        (x.next_draw_number, x.next_ticket_number, dict(x.schedule)) for x in lotteries
    ]
    assert fund.balance + sum(x.balance for x in jackpots) == initial_total
    ledger = [x for x in fake.added if isinstance(x, LedgerTransaction)]
    assert len(ledger) == 6
    assert sum(x.amount for x in ledger) == 0
    assert all(x.details["economy_step"] == STEP for x in ledger)
    assert {x.account_kind for x in ledger} == {
        LedgerAccountKind.JACKPOT,
        LedgerAccountKind.KASPER_FUND,
    }
    assert len([x for x in fake.added if isinstance(x, AdminAuditLog)]) == 3
    assert control.paused and control.epoch == 2 and control.recovery_after is None
    repeat = BatchSession(scalar_values=[object(), control])
    result = await ThemedEconomyService(cast(AsyncSession, repeat)).apply(
        owner_id=owner
    )
    assert result["already_applied"] is True
    assert not repeat.added


@pytest.mark.parametrize(
    "failure", ["owner", "open", "initial", "draw", "ticket", "missing", "shape"]
)
async def test_batch_refuses_unsafe_transition_before_any_money_movement(failure):
    control, lotteries, jackpots, fund = batch_objects()
    if failure == "open":
        control.paused = False
    if failure == "initial":
        control.applied_steps = {}
    if failure == "shape":
        lotteries[0].max_number = 16
    fake = BatchSession(
        scalar_values=[
            None if failure == "owner" else object(),
            control,
            uuid4() if failure == "draw" else None,
            uuid4() if failure == "ticket" else None,
            fund,
        ],
        scalar_collections=[
            lotteries[:-1] if failure == "missing" else lotteries,
            jackpots,
        ],
    )
    with pytest.raises((ConfigurationError, InvalidStateTransition)):
        await ThemedEconomyService(cast(AsyncSession, fake)).apply(owner_id=uuid4())
    assert not fake.added
