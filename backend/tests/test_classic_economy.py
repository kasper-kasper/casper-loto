"""Approved 40/60 splits, exact highest tiers and 600-ticket draw limits."""

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.classic_economy import STEP, TERMS, ClassicEconomyService
from k_loto.application.weekly import LotteryTicketPurchaseService
from k_loto.domain.errors import InvalidTicket
from k_loto.domain.lottery_rules import (
    CLASSIC_6_36_RULES,
    GRAND_FIXED_RULES,
    PSS_CASPER_BALL_RULES,
    SettlementTicket,
    get_lottery_rules,
)
from k_loto.infrastructure.database.models import AdminAuditLog, LedgerTransaction
from test_themed_economy import BatchSession, batch_objects
from test_weekly_application import FakeSession, build_purchase_accounts

PAYOUTS = (
    {0: 0, 1: 0, 2: 30_000, 3: 140_000, 4: 1_000_000, 5: 7_000_000},
    {
        0: 0,
        1: 25_000,
        10: 0,
        11: 100_000,
        20: 50_000,
        21: 100_000,
        30: 200_000,
        31: 400_000,
        40: 1_000_000,
        41: 5_000_000,
        50: 25_000_000,
    },
    {
        0: 0,
        1: 0,
        2: 0,
        10: 0,
        11: 0,
        12: 0,
        20: 75_000,
        21: 150_000,
        22: 300_000,
        30: 650_000,
        31: 850_000,
        32: 1_200_000,
        40: 1_500_000,
        41: 3_000_000,
        42: 8_000_000,
        50: 30_000_000,
        51: 60_000_000,
    },
)


def combination(rule, matches):
    a, b = divmod(matches, 10) if rule.secondary_numbers_to_pick else (matches, 0)
    count = rule.display_primary_numbers_to_pick
    main = (*range(1, a + 1), *range(10, 10 + count - a))
    offset = rule.secondary_storage_offset
    special = (
        *range(offset + 1, offset + b + 1),
        *range(offset + 3, offset + 3 + rule.secondary_numbers_to_pick - b),
    )
    return (*main, *special)


@pytest.mark.parametrize("index", range(3))
def test_every_category_pays_only_the_highest_and_retains_the_original_format(index):
    _, rule, price, base = TERMS[index]
    legacy = (CLASSIC_6_36_RULES, PSS_CASPER_BALL_RULES, GRAND_FIXED_RULES)[index]
    fields = (
        "numbers_to_pick",
        "max_number",
        "primary_numbers_to_pick",
        "primary_max_number",
        "secondary_numbers_to_pick",
        "secondary_max_number",
        "secondary_storage_offset",
        "minimum_number",
        "allow_repeats",
        "ordered",
        "server_code_max",
        "jackpot_match",
    )
    assert all(getattr(rule, name) == getattr(legacy, name) for name in fields)
    assert get_lottery_rules(legacy.code) is legacy
    assert get_lottery_rules(rule.code) is rule
    winning = combination(rule, rule.jackpot_match)
    for category, amount in {**PAYOUTS[index], rule.jackpot_match: base + 1}.items():
        ticket = SettlementTicket(
            uuid4(), 1, uuid4(), combination(rule, category), price
        )
        plan = rule.calculate_settlement(
            [ticket],
            winning,
            distribution_balance=0,
            jackpot_balance=base + 1,
            reserve_balance=10_000_000_000,
            base_jackpot=base,
        )
        assert plan.payouts[0].matches == category
        assert plan.payouts[0].amount == amount
    for count in (1, 25, 600):
        quote = rule.quote_purchase([winning] * count, price, price * count)
        assert quote.jackpot_contribution == price * 2 // 5 * count
        assert quote.distribution_contribution == price * 3 // 5 * count
    # Payouts stored under old codes must not inherit the new fixed table or split.
    assert legacy.jackpot_contribution(price) == price
    assert legacy.fixed_payouts != rule.fixed_payouts


@pytest.mark.parametrize("code,rule,price,base", TERMS)
async def test_real_purchase_credits_40_percent_and_enforces_600_across_purchases(
    code, rule, price, base
):
    now = datetime(2026, 10, 18, tzinfo=UTC)
    user, lottery, draw, balance, jackpot, _ = build_purchase_accounts(now)
    lottery.code, lottery.ruleset_code = code, rule.code
    lottery.numbers_to_pick, lottery.max_number = rule.numbers_to_pick, rule.max_number
    lottery.ticket_price = price
    lottery.max_tickets_per_purchase = lottery.max_tickets_per_user_per_draw = 600
    balance.amount = 100_000_000
    jackpot.balance, jackpot.base_amount = base, base
    numbers = combination(rule, rule.jackpot_match)
    for existing, count in ((599, 1), (600, 1), (0, 600)):
        if existing == 0:
            # Another draw can be bought on the same purchase day: no daily cap.
            draw.id = uuid4()
            draw.ticket_count = draw.total_sales = 0
            draw.scheduled_at += timedelta(days=7)
            draw.sales_close_at += timedelta(days=7)
        fake = FakeSession(
            scalar_values=[None, lottery, jackpot, None, draw, existing, balance]
        )
        service = LotteryTicketPurchaseService(
            cast(AsyncSession, fake), lottery_code=code
        )
        before = jackpot.balance
        if existing == 600:
            with pytest.raises(InvalidTicket, match="per-player ticket limit"):
                await service.purchase(
                    user_id=user,
                    combinations=[numbers],
                    idempotency_key="over",
                    now=now,
                )
            assert not fake.added and jackpot.balance == before
            continue
        await service.purchase(
            user_id=user,
            combinations=[numbers] * count,
            idempotency_key=f"buy-{count}",
            now=now,
        )
        ledger = [x for x in fake.added if isinstance(x, LedgerTransaction)]
        assert jackpot.balance - before == count * price * 2 // 5
        assert sum(x.amount for x in ledger) == -(count * price * 3 // 5)
        assert ledger[0].details["burned_cas"] == count * price * 3 // 5


@pytest.mark.parametrize("per_purchase", [100, 1000])
async def test_paused_batch_is_audited_preserves_counters_and_does_not_repeat(
    per_purchase,
):
    control, lotteries, jackpots, fund = batch_objects(TERMS)
    for lottery in lotteries:
        lottery.max_tickets_per_purchase = per_purchase
    counters = [
        (x.next_draw_number, x.next_ticket_number, dict(x.schedule)) for x in lotteries
    ]
    total = fund.balance + sum(x.balance for x in jackpots)
    fake = BatchSession(
        scalar_values=[object(), control, None, None, fund],
        scalar_collections=[lotteries, jackpots],
    )
    owner = uuid4()
    await ClassicEconomyService(cast(AsyncSession, fake)).apply(owner_id=owner)
    for lottery, jackpot, (_, rule, price, base) in zip(
        lotteries, jackpots, TERMS, strict=True
    ):
        assert lottery.ticket_price == price and lottery.ruleset_code == rule.code
        assert lottery.max_tickets_per_user_per_draw == 600
        assert lottery.max_tickets_per_purchase == min(per_purchase, 600)
        assert jackpot.balance == jackpot.base_amount == base
    assert counters == [
        (x.next_draw_number, x.next_ticket_number, dict(x.schedule)) for x in lotteries
    ]
    assert fund.balance + sum(x.balance for x in jackpots) == total
    ledger = [x for x in fake.added if isinstance(x, LedgerTransaction)]
    assert len(ledger) == 6 and sum(x.amount for x in ledger) == 0
    assert all(x.details["economy_step"] == STEP for x in ledger)
    assert len([x for x in fake.added if isinstance(x, AdminAuditLog)]) == 3
    assert control.paused and control.epoch == 2 and control.recovery_after is None
    repeat = BatchSession(scalar_values=[object(), control])
    assert (
        await ClassicEconomyService(cast(AsyncSession, repeat)).apply(owner_id=owner)
    )["already_applied"]
    assert not repeat.added
