"""Epic boundaries, bounded projections and ten-ticket reward idempotency."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, update

from k_loto.application.achievement_catalog import import_catalog
from k_loto.application.achievement_progress import ExtendedProgress
from k_loto.application.achievement_results import ticket_result
from k_loto.application.achievements import execute_rewards, record_activity
from k_loto.application.epic_achievements import epic_catalog
from k_loto.application.rare_achievements import rare_catalog
from k_loto.domain.achievements import Condition, RewardSpec
from k_loto.domain.lottery_rules import (
    BALL_ECONOMY_RULES,
    CLASSIC_ECONOMY_RULES,
    CODE_RULES,
    GRAND_ECONOMY_RULES,
    PULSE_RULES,
)
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementReward,
    AchievementRuntime,
)
from k_loto.infrastructure.database.models import Balance, Draw, Ticket, TicketSource
from test_achievements import entry, launch, metrics, quiet, seed, tickets
from test_achievements import pg as pg
from test_common_achievements import seed_catalog_games
from test_uncommon_achievements import open_gift_game


def test_approved_catalog_totals_and_packages():
    entries = epic_catalog()
    assert len(entries) == len({e.code for e in entries}) == 17
    assert all(e.rarity == "epic" and e.active and e.flavor for e in entries)
    cash = [r.amount for e in entries for r in e.rewards if r.type == "cas"]
    assert sum(cash) == 98_500_000
    assert sorted(cash)[-2:] == [8_000_000, 20_000_000]
    assert min(cash) == 3_000_000
    assert sum(r.type == "ticket" for e in entries for r in e.rewards) == 165
    cases = [r.amount for e in entries for r in e.rewards if r.type == "case"]
    assert sorted(cases) == [1, 1] + [4] * 15 and sum(cases) == 62
    by_title = {e.title: e for e in entries}
    for title, amount in [("Без права на ошибку", 10), ("Большая коллекция", 5)]:
        gifts = [r for r in by_title[title].rewards if r.type == "ticket"]
        assert len(gifts) == amount and all(r.lottery == "weekly" for r in gifts)
    assert by_title["Тут всё моё"].condition.conditions[0].target == 100_000
    assert by_title["Мастер четырнадцати"].condition.conditions[0].target == 14


@pytest.mark.parametrize(
    "suffix,rules,match,accepted",
    [
        ("classic_five", CLASSIC_ECONOMY_RULES, 5, True),
        ("classic_five", CLASSIC_ECONOMY_RULES, 6, False),
        ("ball_five_zero", BALL_ECONOMY_RULES, 50, True),
        ("ball_five_zero", BALL_ECONOMY_RULES, 51, False),
        ("grand_near_crown", GRAND_ECONOMY_RULES, 50, True),
        ("grand_near_crown", GRAND_ECONOMY_RULES, 51, True),
        ("grand_near_crown", GRAND_ECONOMY_RULES, 52, False),
        ("code_four_thrice", CODE_RULES, 4, True),
        ("code_four_thrice", CODE_RULES, 5, False),
        ("pulse_two_two_twice", PULSE_RULES, 220, True),
        ("pulse_two_two_twice", PULSE_RULES, 221, True),
    ],
)
def test_exact_game_result_boundaries(suffix, rules, match, accepted):
    e = next(e for e in epic_catalog() if e.code == f"epic_{suffix}")
    result = ticket_result(
        SimpleNamespace(
            matches=match, prize_amount=1, purchase_price=10, bingo_result=None
        ),
        SimpleNamespace(
            configuration_snapshot={"ruleset_code": rules.code}, is_distribution=False
        ),
        SimpleNamespace(
            code=e.condition.conditions[0].lottery, ruleset_code=rules.code
        ),
    )
    assert any(c.matches_result(result) for c in e.condition.conditions) is accepted


@pytest.mark.parametrize("value", [[], [-1], [True], list(range(17))])
def test_match_set_is_bounded_and_strict(value):
    with pytest.raises(ValidationError):
        Condition(metric="result_count", target=3, matches_any=value)


def test_mixed_dual_counter_and_case_quantity_validation():
    c = next(
        e for e in epic_catalog() if e.title == "Две стороны медали"
    ).condition.conditions[0]
    reordered = c.model_copy(update={"matches_any": [21, 12, 12], "target": 4})
    assert c.key == reordered.key
    assert (
        sum(
            c.matches_result(dict(lottery="dual", matches=m, prize=1))
            for m in [12, 21, 12, 22]
        )
        == 3
    )
    assert not c.matches_result(dict(lottery="dual", matches=12, prize=0))
    assert c.accepts(3) and not c.accepts(2)
    for amount in [1, 4]:
        assert RewardSpec(type="case", amount=amount, planned=True).amount == amount
    for amount in [0, 201, True]:
        with pytest.raises(ValidationError):
            RewardSpec(type="case", amount=amount, planned=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "order,expected", [([0, 1, 2, 3, 4], 5), ([4, 0, 1, 3, 2], 5), ([0, 1, 3, 4, 5], 3)]
)
async def test_five_adjacent_draws_including_out_of_order_and_gap(pg, order, expected):
    uid, lid, _ = await seed(pg)
    start = datetime.now(UTC) - timedelta(days=3)
    ids = [uuid4() for _ in range(6)]
    async with pg() as s, s.begin():
        for i, did in enumerate(ids):
            s.add(
                Draw(
                    id=did,
                    lottery_id=lid,
                    public_number=10 + i,
                    scheduled_at=start + timedelta(hours=i),
                    sales_close_at=start,
                    status="COMPLETED",
                    executed_at=start,
                    configuration_snapshot={},
                )
            )
    async with pg() as s, s.begin():
        p, m = ExtendedProgress(s), {}
        for i in order:
            draw = await s.get(Draw, ids[i])
            await p.win(
                uid, dict(lottery="test", prize=1), draw.scheduled_at, m, draw=draw
            )
        assert m["consecutive_winning_draws"] == expected
        assert all(len(side) <= 4 for sides in p.neighbours.values() for side in sides)


@pytest.mark.asyncio
async def test_fifty_consecutive_and_hundred_total_days_are_independent(pg):
    uid, _, _ = await seed(pg)
    await seed_catalog_games(pg)
    # The full production conditions are used; only rewards are omitted in this fixture.
    entries = [
        e.model_copy(update={"rewards": []})
        for e in epic_catalog()
        if e.title in {"Ты ещё здесь?!", "Старые знакомые"}
    ]
    await launch(pg, entries)
    start = datetime.now(UTC) + timedelta(days=1)
    for i in list(range(50)) + list(range(60, 110)):
        async with pg() as s, s.begin():
            await record_activity(s, uid, start + timedelta(days=i))
            await record_activity(s, uid, start + timedelta(days=i, minutes=1))
    await quiet(pg)
    m = await metrics(pg, uid)
    assert m["max_streak"] == 50 and m["active_days"] == 100
    async with pg() as s:
        assert set(await s.scalars(select(AchievementAward.code))) == {
            e.code for e in entries
        }


@pytest.mark.asyncio
async def test_ten_grand_gifts_and_four_planned_cases_survive_parallel_replay(pg):
    uid, lid, did = await seed(pg)
    await open_gift_game(pg, "weekly")
    original = next(e for e in epic_catalog() if e.title == "Без права на ошибку")
    await launch(
        pg, [entry(target=1, rewards=[r.model_dump() for r in original.rewards])]
    )
    await tickets(pg, uid, lid, did, 1)
    await quiet(pg)
    async with pg() as s:
        award = await s.scalar(select(AchievementAward))
        award_id = award.id

    async def replay():
        async with pg() as s, s.begin():
            await execute_rewards(s, award_id, datetime.now(UTC))

    await asyncio.gather(*(replay() for _ in range(3)))
    async with pg() as s:
        assert (
            await s.scalar(
                select(func.count())
                .select_from(Ticket)
                .where(Ticket.source == TicketSource.GIFT)
            )
            == 10
        )
        assert (await s.get(Balance, uid)).amount == 6_000_000
        parts = list(
            await s.scalars(
                select(AchievementReward).where(AchievementReward.award_id == award_id)
            )
        )
        assert len(parts) == 12
        assert (await s.get(AchievementAward, award_id)).reward_status == "planned"
        assert sum(p.status == "completed" for p in parts) == 11
        assert (await s.get(AchievementRuntime, 1)).enabled
    assert (await metrics(pg, uid))["paid_tickets"] == 1


@pytest.mark.asyncio
async def test_mixed_dual_filter_replays_existing_settled_events_once(pg):
    uid, lid, did = await seed(pg)
    await seed_catalog_games(pg)
    async with pg() as s, s.begin():
        from k_loto.domain.lottery_rules import DUAL_ECONOMY_RULES
        from k_loto.infrastructure.database.models import Lottery

        game = await s.get(Lottery, lid)
        game.code = "test-dual"
        draw = await s.get(Draw, did)
        draw.configuration_snapshot = {"ruleset_code": DUAL_ECONOMY_RULES.code}
    await launch(pg, rare_catalog())
    ids = await tickets(pg, uid, lid, did, 4)
    await quiet(pg)
    async with pg() as s, s.begin():
        for tid, match in zip(ids, [12, 21, 12, 22], strict=True):
            await s.execute(
                update(Ticket)
                .where(Ticket.id == tid)
                .values(
                    status="SETTLED",
                    matches=match,
                    prize_amount=10,
                    settled_at=datetime.now(UTC),
                )
            )
        await s.execute(
            update(Draw)
            .where(Draw.id == did)
            .values(status="COMPLETED", executed_at=datetime.now(UTC))
        )
    await quiet(pg)
    e = next(e for e in epic_catalog() if e.title == "Две стороны медали")
    c = e.condition.conditions[0].model_copy(update={"lottery": "test-dual"})
    e = e.model_copy(
        update={
            "condition": e.condition.model_copy(update={"conditions": [c]}),
            "rewards": [],
        }
    )
    for _ in range(2):
        async with pg() as s, s.begin():
            await import_catalog(s, [e])
        await quiet(pg)
    assert (await metrics(pg, uid))[c.key] == 3
    async with pg() as s:
        assert (
            await s.scalar(
                select(func.count())
                .select_from(AchievementAward)
                .where(AchievementAward.code == e.code)
            )
            == 1
        )
