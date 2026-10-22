"""Rare catalogue, bounded draw/day metrics and replay correctness."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select, update

from k_loto.application.achievement_catalog import import_catalog
from k_loto.application.achievement_progress import ExtendedProgress
from k_loto.application.achievement_results import ticket_result
from k_loto.application.achievements import record_activity
from k_loto.application.common_achievements import common_catalog
from k_loto.application.epic_achievements import epic_catalog
from k_loto.application.rare_achievements import rare_catalog
from k_loto.application.uncommon_achievements import uncommon_catalog
from k_loto.domain.lottery_rules import (
    BALL_ECONOMY_RULES,
    BINGO_ECONOMY_RULES,
    CLASSIC_ECONOMY_RULES,
    CODE_RULES,
    DUAL_ECONOMY_RULES,
    FAST_RULES,
    GRAND_ECONOMY_RULES,
    PLL_ECONOMY_RULES,
    PULSE_RULES,
    SEPTEMBER_ECONOMY_RULES,
)
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementDay,
    AchievementEvent,
    AchievementRuntime,
    AchievementWinningDraw,
)
from k_loto.infrastructure.database.models import Draw, Lottery, Ticket
from test_achievements import entry, launch, metrics, quiet, seed, tickets
from test_achievements import pg as pg
from test_common_achievements import seed_catalog_games


def test_exact_approved_catalog_and_activity_unchanged():
    entries = rare_catalog()
    assert len(entries) == len({e.code for e in entries}) == 20
    cash = [r.amount for e in entries for r in e.rewards if r.type == "cas"]
    assert min(cash) == 400_000 and max(cash) == 900_000 and sum(cash) == 12_300_000
    assert sum(r.type == "ticket" for e in entries for r in e.rewards) == 80
    assert sum(r.type == "case" and r.planned for e in entries for r in e.rewards) == 10
    assert all(e.rarity == "rare" and e.active and e.flavor for e in entries)
    by_title = {
        e.title: e.condition.conditions[0]
        for e in common_catalog() + uncommon_catalog() + entries
    }
    assert [
        (by_title[t].metric, by_title[t].target)
        for t in ["Ну наконец-то", "Роднуля", "Братик", "Прописался", "Мы знакомы?"]
    ] == [
        ("active_days", 3),
        ("max_streak", 7),
        ("active_days", 14),
        ("max_streak", 21),
        ("active_days", 30),
    ]


@pytest.mark.parametrize(
    "suffix,rules,match,moves,accepted",
    [
        ("code_four", CODE_RULES, 4, None, True),
        ("code_four", CODE_RULES, 5, None, False),
        ("pulse_two_two", PULSE_RULES, 220, None, True),
        ("pulse_two_two", PULSE_RULES, 221, None, True),
        ("pulse_two_two", PULSE_RULES, 210, None, False),
        ("bingo_forty", BINGO_ECONOMY_RULES, 12, [18, 34, 40], True),
        ("bingo_forty", BINGO_ECONOMY_RULES, 12, [18, 34, 41], False),
        ("bingo_forty", BINGO_ECONOMY_RULES, 12, [18, 34, 61], False),
        ("bingo_forty", BINGO_ECONOMY_RULES, 12, [18, 34], False),
    ],
)
def test_code_pulse_and_full_card_boundaries(suffix, rules, match, moves, accepted):
    c = next(
        e for e in rare_catalog() if e.code == f"rare_{suffix}"
    ).condition.conditions[0]
    result = ticket_result(
        SimpleNamespace(
            matches=match,
            prize_amount=1,
            purchase_price=10,
            bingo_result={"moves": moves, "amounts": [1, 0, 0, 0]} if moves else None,
        ),
        SimpleNamespace(
            configuration_snapshot={"ruleset_code": rules.code}, is_distribution=False
        ),
        SimpleNamespace(code=c.lottery, ruleset_code=rules.code),
    )
    assert c.matches_result(result) is accepted


def test_100x_uses_exact_sum_of_one_ticket_and_repeated_filters_share_counters():
    entries = {e.title: e for e in rare_catalog()}
    c = entries["Умножить"].condition.conditions[0]
    assert not c.matches_result(
        dict(lottery="september", prize=333_299, standard_price=3333)
    )
    assert c.matches_result(
        dict(lottery="september", prize=333_300, standard_price=3333)
    )
    shared = {e.title: e.condition.conditions[0] for e in uncommon_catalog()}
    assert (
        entries["Шестёрка"].condition.conditions[0].key == shared["Почти снайпер"].key
    )
    assert entries["Третий звонок"].condition.conditions[0].key == shared["Дзынь!"].key
    assert (
        entries["Два сердца"].condition.conditions[0].key
        == shared["Сердечко ёкнуло"].key
    )
    dual = entries["Между двух миров"].condition
    assert dual.mode == "any" and len(dual.conditions) == 2


@pytest.mark.asyncio
async def test_fast_day_mask_distinct_games_and_midnight(pg):
    uid, _, _ = await seed(pg)
    async with pg() as s, s.begin():
        p = ExtendedProgress(s)
        m = {}
        day = datetime(2026, 10, 20, 20, 59, tzinfo=UTC)
        for code in ["flash", "flash", "shadow", "khan"]:
            await p.win(uid, {"lottery": code, "prize": 1}, day, m)
        assert m["daily_fast_winning_games"] == 2
        await p.win(uid, {"lottery": "pulse", "prize": 0}, day, m)
        await p.win(
            uid, {"lottery": "pulse", "prize": 1}, day + timedelta(minutes=2), m
        )
        assert m["daily_fast_winning_games"] == 2
        await p.win(uid, {"lottery": "pulse", "prize": 1}, day, m)
        assert m["daily_fast_winning_games"] == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "order,expected", [([0, 2, 1], 3), ([0, 2, 3], 2), ([2, 1, 0], 3)]
)
async def test_three_neighbouring_draws_late_middle_and_nonwinning_gap(
    pg, order, expected
):
    uid, lid, _ = await seed(pg)
    start = datetime.now(UTC) + timedelta(days=10)
    ids = [uuid4() for _ in range(4)]
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
        p = ExtendedProgress(s)
        m = {}
        for i in order:
            d = await s.get(Draw, ids[i])
            await p.win(uid, {"lottery": "test", "prize": 1}, d.scheduled_at, m, draw=d)
        assert m["consecutive_winning_draws"] == expected


@pytest.mark.asyncio
async def test_thousand_tickets_and_21_streak_30_separate_days(pg):
    uid, lid, did = await seed(pg)
    await seed_catalog_games(pg)
    await launch(pg, common_catalog() + uncommon_catalog() + rare_catalog())
    await tickets(pg, uid, lid, did, 1000)
    base = datetime.now(UTC) + timedelta(days=1)
    for i in list(range(21)) + list(range(30, 39)):
        async with pg() as s, s.begin():
            await record_activity(s, uid, base + timedelta(days=i))
            await record_activity(s, uid, base + timedelta(days=i, minutes=1))
    await quiet(pg)
    m = await metrics(pg, uid)
    assert (
        m["paid_tickets"] == 1000 and m["active_days"] == 30 and m["max_streak"] == 21
    )
    async with pg() as s:
        codes = set(await s.scalars(select(AchievementAward.code)))
        assert {
            "rare_thousand_tickets",
            "rare_twenty_one_streak",
            "rare_thirty_days",
            "uncommon_seven_day_streak",
            "uncommon_fourteen_days",
        } <= codes


@pytest.mark.asyncio
@pytest.mark.parametrize("epic", [False, True])
async def test_upgrade_replays_wins_not_paid_days_and_preserves_partial_cursor(
    pg, epic
):
    uid, lid, did = await seed(pg)
    await seed_catalog_games(pg)
    await launch(pg, [entry(metric="daily_play_types", target=3)])
    if epic:
        async with pg() as s, s.begin():
            await import_catalog(s, rare_catalog())
    ids = await tickets(pg, uid, lid, did, 155)
    await quiet(pg)
    now = datetime.now(UTC)
    async with pg() as s, s.begin():
        await s.execute(
            update(Ticket)
            .where(Ticket.id.in_(ids))
            .values(status="SETTLED", matches=3, prize_amount=10_000, settled_at=now)
        )
        await s.execute(
            update(Draw)
            .where(Draw.id == did)
            .values(status="COMPLETED", executed_at=now)
        )
    # Process exactly the first page, then import the new catalogue under its lock.
    from k_loto.application.achievements import process_one

    assert await process_one(pg)
    async with pg() as s, s.begin():
        e = await s.scalar(
            select(AchievementEvent).where(AchievementEvent.kind == "draw")
        )
        assert e.cursor and e.processed_at is None
        started = (await s.get(AchievementRuntime, 1)).started_at
        before = await s.get(
            AchievementDay, (uid, now.astimezone(ZoneInfo("Europe/Moscow")).date())
        )
        counts = dict(before.play_counts)
        await import_catalog(s, epic_catalog() if epic else rare_catalog())
        assert (await s.get(AchievementRuntime, 1)).projection_revision == (
            3 if epic else 2
        )
        assert before.play_counts == counts
    await quiet(pg)
    async with pg() as s:
        row = await s.get(AchievementWinningDraw, (uid, did))
        assert row.tickets == 155
        assert (await s.get(AchievementRuntime, 1)).started_at == started
        codes = set(await s.scalars(select(AchievementAward.code)))
        assert {
            "rare_hundred_fifty_wins",
            "rare_five_draw_wins",
            "rare_million_prizes",
        } <= codes
    m = await metrics(pg, uid)
    assert (
        m["winning_tickets"] == 155
        and m["max_draw_winning_tickets"] == 155
        and m["won_cas"] == 1_550_000
    )
    assert m["paid_tickets"] == 155
    async with pg() as s, s.begin():
        await import_catalog(s, rare_catalog())
    await quiet(pg)
    assert (await metrics(pg, uid))["max_draw_winning_tickets"] == 155


@pytest.mark.asyncio
async def test_repeated_results_same_draw_and_ten_real_game_ids(pg):
    uid, _, _ = await seed(pg)
    await seed_catalog_games(pg)
    await launch(pg, common_catalog() + uncommon_catalog() + rare_catalog())
    fixtures = [
        ("flash", FAST_RULES, [4, 4]),
        ("shadow", CODE_RULES, [4]),
        ("pulse", PULSE_RULES, [220, 120, 121]),
        ("khan", CLASSIC_ECONOMY_RULES, [4, 4]),
        ("pss", BALL_ECONOMY_RULES, [20, 20, 20]),
        ("dual", DUAL_ECONOMY_RULES, [12, 21]),
        ("bingo", BINGO_ECONOMY_RULES, [12]),
        ("september", SEPTEMBER_ECONOMY_RULES, [2]),
        ("pll", PLL_ECONOMY_RULES, [3]),
        ("weekly", GRAND_ECONOMY_RULES, [20]),
    ]
    now = datetime.now(UTC)
    at = now.replace(hour=12, minute=0, second=0)
    for i, (code, rules, matches) in enumerate(fixtures):
        async with pg() as s, s.begin():
            lid = await s.scalar(select(Lottery.id).where(Lottery.code == code))
            d = Draw(
                id=uuid4(),
                lottery_id=lid,
                public_number=8000 + i,
                scheduled_at=at + timedelta(minutes=i),
                sales_close_at=at - timedelta(minutes=1),
                configuration_snapshot={"ruleset_code": rules.code, "ticket_price": 10},
            )
            s.add(d)
            did = d.id
        ids = await tickets(pg, uid, lid, did, len(matches), start=8000)
        async with pg() as s, s.begin():
            for tid, match in zip(ids, matches, strict=True):
                await s.execute(
                    update(Ticket)
                    .where(Ticket.id == tid)
                    .values(
                        status="SETTLED",
                        matches=match,
                        prize_amount=100_000,
                        settled_at=now,
                        bingo_result={"moves": [18, 34, 40], "amounts": [25_000] * 4}
                        if code == "bingo"
                        else None,
                    )
                )
            await s.execute(
                update(Draw)
                .where(Draw.id == did)
                .values(status="COMPLETED", executed_at=now)
            )
    await quiet(pg)
    async with pg() as s:
        codes = set(await s.scalars(select(AchievementAward.code)))
        assert {
            "rare_hundredfold_win",
            "rare_flash_four",
            "rare_code_four",
            "rare_pulse_two_two",
            "rare_classic_four_twice",
            "rare_ball_two_zero_thrice",
            "rare_dual_mixed",
            "rare_bingo_forty",
            "rare_eight_winning_games",
            "rare_million_prizes",
            "rare_daily_fast_wins",
            "rare_flash_four_twice",
            "rare_pulse_one_two_twice",
            "rare_ten_games",
        } <= codes
        assert "rare_five_draw_wins" not in codes
        assert "rare_three_consecutive_wins" not in codes
    m = await metrics(pg, uid)
    assert m["max_draw_winning_tickets"] == 3
    assert m["winning_tickets"] == 17 and m["prizes_count"] == 20
    assert m["lotteries_count"] == 10 and m["winning_lotteries"] == 10
