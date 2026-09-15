"""Daily interesting-fact candidate generation."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.application.interesting_facts import (
    FactDraw,
    FactLottery,
    FactTicketStats,
    InterestingFactService,
    build_fact_candidates,
)


def test_candidate_builder_covers_required_fact_types_and_ranks_by_score() -> None:
    now = datetime(2026, 9, 15, 1, tzinfo=UTC)
    lottery_id = UUID(int=71)
    lottery = FactLottery(
        id=lottery_id,
        code="khan",
        name="6 из 36",
        ruleset_code="daily_6_36",
        max_number=36,
        current_jackpot=3_000_000,
        base_jackpot=1_000_000,
        historical_jackpot=2_500_000,
        jackpot_drought=12,
    )
    draws = [
        FactDraw(
            lottery_id=lottery_id,
            scheduled_at=now - timedelta(hours=index),
            winning_numbers=(1, 2, 3, 4, 5, 6),
            ticket_count=20 + index,
            total_sales=2_000 + index * 100,
            jackpot_opening=1_000_000,
            jackpot_closing=1_100_000,
        )
        for index in range(10)
    ]
    stats = FactTicketStats(
        lottery_id=lottery_id,
        daily_tickets=10,
        daily_winners=8,
        daily_largest_win=900_000,
        weekly_tickets=70,
        weekly_winners=20,
        weekly_largest_win=1_500_000,
        monthly_tickets=100,
        monthly_winners=20,
    )

    candidates = build_fact_candidates([lottery], draws, [stats], now=now)
    types = {candidate.fact_type for candidate in candidates}

    assert {
        "jackpot_drought",
        "record_current_jackpot",
        "jackpot_growth",
        "frequent_numbers",
        "overdue_numbers",
        "daily_winner_leader",
        "largest_daily_win",
        "largest_weekly_win",
        "unusual_win_rate",
    }.issubset(types)
    assert [item.score for item in candidates] == sorted(
        (item.score for item in candidates), reverse=True
    )
    assert all(item.numeric_values for item in candidates)


def test_bingo_does_not_create_misleading_number_frequency_facts() -> None:
    now = datetime(2026, 9, 15, 1, tzinfo=UTC)
    lottery_id = UUID(int=72)
    lottery = FactLottery(
        lottery_id,
        "bingo",
        "Kasper Bingo",
        "bingo_3x5_1_60",
        60,
        1_000_000,
        1_000_000,
        1_000_000,
        0,
    )
    draws = [
        FactDraw(
            lottery_id,
            now - timedelta(days=index),
            tuple(range(1, 61)),
            10,
            1_000,
            1_000_000,
            1_000_000,
        )
        for index in range(5)
    ]

    types = {
        item.fact_type for item in build_fact_candidates([lottery], draws, [], now=now)
    }

    assert "frequent_numbers" not in types
    assert "overdue_numbers" not in types
    assert "frequent_pair" not in types


class _NoopTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *_args: object) -> None:
        return None


class _ExistingBatchSession:
    def begin(self) -> _NoopTransaction:
        return _NoopTransaction()

    async def __aenter__(self) -> "_ExistingBatchSession":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def scalar(self, _statement: object) -> None:
        return None


async def test_daily_generation_skips_snapshot_when_batch_already_exists() -> None:
    factory = cast(
        async_sessionmaker[AsyncSession],
        cast(Any, lambda: _ExistingBatchSession()),
    )

    generated = await InterestingFactService(factory).run_if_due(
        now=datetime(2026, 9, 15, 1, tzinfo=UTC)
    )

    assert generated is False
