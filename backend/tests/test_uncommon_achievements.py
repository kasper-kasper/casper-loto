"""Uncommon rules, sparse projections and once-only reward packs on PostgreSQL."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from k_loto.application.achievement_catalog import import_catalog
from k_loto.application.achievement_progress import ExtendedProgress
from k_loto.application.achievement_results import ticket_result
from k_loto.application.achievements import execute_rewards, record_activity
from k_loto.application.uncommon_achievements import uncommon_catalog
from k_loto.application.weekly import KASPER_FUND_ID, draw_configuration_snapshot
from k_loto.domain.enums import LotteryKind, TicketSource
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
    AchievementReward,
    AchievementRuntime,
)
from k_loto.infrastructure.database.models import (
    Balance,
    BingoPoolTicket,
    Draw,
    JackpotAccount,
    KasperFundAccount,
    Lottery,
    Ticket,
)
from test_achievements import entry, launch, metrics, quiet, seed, tickets
from test_achievements import pg as pg
from test_common_achievements import seed_catalog_games


def test_catalog_exact_rewards_and_three_owner_additions():
    entries = uncommon_catalog()
    assert len(entries) == len({e.code for e in entries}) == 23
    assert all(e.rarity == "uncommon" and e.flavor and e.active for e in entries)
    assert (
        sum(r.amount for e in entries for r in e.rewards if r.type == "cas")
        == 3_575_000
    )
    assert sum(r.type == "ticket" for e in entries for r in e.rewards) == 50
    assert sum(r.type == "case" and r.planned for e in entries for r in e.rewards) == 8
    by_title = {e.title: e for e in entries}
    for title, game, amount in [
        ("Я календарь переверну", "september", 3),
        ("Богач", "weekly", 1),
        ("По чуть-чуть", "pll", 2),
        ("БИНГО на минималках", "bingo", 3),
        ("Маленький Гранд", "weekly", 3),
        ("Три из шести", "khan", 3),
        ("Почти снайпер", "khan", 5),
    ]:
        gifts = [r for r in by_title[title].rewards if r.type == "ticket"]
        assert len(gifts) == amount and all(
            r.lottery == game and r.amount == 1 for r in gifts
        )


@pytest.mark.parametrize(
    "suffix,rules,matches,moves,accepted",
    [
        ("flash_three", FAST_RULES, 3, None, True),
        ("flash_three", FAST_RULES, 4, None, False),
        ("code_three", CODE_RULES, 3, None, True),
        ("code_three", CODE_RULES, 4, None, False),
        ("pulse_one_two", PULSE_RULES, 120, None, True),
        ("pulse_one_two", PULSE_RULES, 121, None, True),
        ("pulse_one_two", PULSE_RULES, 210, None, False),
        ("september_two", SEPTEMBER_ECONOMY_RULES, 2, None, True),
        ("september_two", SEPTEMBER_ECONOMY_RULES, 3, None, False),
        ("pll_three", PLL_ECONOMY_RULES, 3, None, True),
        ("bingo_first_row", BINGO_ECONOMY_RULES, 12, [18, 30, 40], True),
        ("bingo_first_row", BINGO_ECONOMY_RULES, 12, [19, 30, 40], False),
        ("classic_three", CLASSIC_ECONOMY_RULES, 3, None, True),
        ("classic_three", CLASSIC_ECONOMY_RULES, 4, None, False),
        ("classic_four", CLASSIC_ECONOMY_RULES, 4, None, True),
        ("ball_two_zero", BALL_ECONOMY_RULES, 20, None, True),
        ("ball_two_zero", BALL_ECONOMY_RULES, 21, None, False),
        ("grand_two", GRAND_ECONOMY_RULES, 20, None, True),
        ("grand_two", GRAND_ECONOMY_RULES, 21, None, True),
        ("grand_two", GRAND_ECONOMY_RULES, 22, None, True),
        ("grand_two", GRAND_ECONOMY_RULES, 30, None, False),
        ("dual_one_one", DUAL_ECONOMY_RULES, 11, None, True),
        ("dual_one_one", DUAL_ECONOMY_RULES, 12, None, False),
    ],
)
def test_game_result_conditions_use_frozen_rules(
    suffix, rules, matches, moves, accepted
):
    condition = next(
        e for e in uncommon_catalog() if e.code == f"uncommon_{suffix}"
    ).condition.conditions[0]
    result = ticket_result(
        SimpleNamespace(
            matches=matches,
            prize_amount=100,
            purchase_price=10,
            bingo_result={"moves": moves, "amounts": [100, 0, 0, 0]} if moves else None,
        ),
        SimpleNamespace(
            configuration_snapshot={"ruleset_code": rules.code}, is_distribution=False
        ),
        SimpleNamespace(code=condition.lottery, ruleset_code=rules.code),
    )
    assert condition.matches_result(result) is accepted


def test_tenfold_threshold_is_exact_integer_and_one_ticket():
    c = next(e for e in uncommon_catalog() if e.title == "Богач").condition.conditions[
        0
    ]
    for prize, accepted in [(33_329, False), (33_330, True), (33_331, True)]:
        assert (
            c.matches_result(
                dict(lottery="september", prize=prize, standard_price=3333)
            )
            is accepted
        )


@pytest.mark.parametrize(
    "title,code,primary,secondary",
    [("Дзынь!", "pss", 2, 0), ("И нашим, и вашим", "dual", 1, 1)],
)
def test_prize_combinations_require_actual_positive_payout(
    title, code, primary, secondary
):
    c = next(e for e in uncommon_catalog() if e.title == title).condition.conditions[0]
    assert not c.matches_result(
        {
            "lottery": code,
            "prize": 0,
            "matches": 0,
            "primary_matches": primary,
            "secondary_matches": secondary,
        }
    )


@pytest.mark.asyncio
async def test_daily_projection_moscow_boundary_separate_groups_and_refund(pg):
    uid, _, _ = await seed(pg)
    async with pg() as s, s.begin():
        p = ExtendedProgress(s)
        m = {}
        before = datetime(2026, 10, 20, 20, 59, tzinfo=UTC)
        after = before + timedelta(minutes=2)
        await p.play(uid, "aurora", before, 1, m, instant=True)
        await p.play(uid, "september", before, 2, m)
        assert m["daily_play_types"] == 2  # special does not also count as draw
        await p.play(uid, "khan", after, 1, m)
        assert m["daily_play_types"] == 2
        await p.play(uid, "flash", before, 1, m)
        assert m["daily_play_types"] == 3
        await p.play(uid, "flash", before, -1, m)
        assert m["daily_play_types"] == 2
        for code, moment in [
            ("flash", before),
            ("flash", before),
            ("shadow", before),
            ("pulse", after),
        ]:
            await p.win(uid, {"lottery": code, "prize": 1}, moment, m)
        assert m["daily_winning_lotteries"] == 2
        await p.win(uid, {"lottery": "pulse", "prize": 1}, before, m)
        assert m["daily_winning_lotteries"] == 3
        await p.win(uid, {"lottery": "pss", "prize": 0}, before, m)
        assert m["daily_winning_lotteries"] == 3


@pytest.mark.asyncio
async def test_adjacent_completed_draws_skip_breaks_duplicates_and_out_of_order(pg):
    uid, lid, _ = await seed(pg)
    base = datetime.now(UTC) + timedelta(days=10)
    ids = [uuid4() for _ in range(4)]
    async with pg() as s, s.begin():
        for i, did in enumerate(ids):
            s.add(
                Draw(
                    id=did,
                    lottery_id=lid,
                    public_number=20 + i,
                    scheduled_at=base + timedelta(hours=i),
                    sales_close_at=base,
                    status="COMPLETED",
                    executed_at=base,
                    configuration_snapshot={},
                )
            )
    async with pg() as s, s.begin():
        p = ExtendedProgress(s)
        m = {}
        result = {"lottery": "test", "prize": 1}
        for i in [0, 0, 2]:
            d = await s.get(Draw, ids[i])
            await p.win(uid, result, d.scheduled_at, m, draw=d)
            assert m["consecutive_winning_draws"] == 1
        d = await s.get(Draw, ids[1])  # late processing of the middle winning draw
        await p.win(uid, result, d.scheduled_at, m, draw=d)
        assert (
            m["consecutive_winning_draws"] == 3
        )  # expanded projection; uncommon still needs 2


@pytest.mark.asyncio
async def test_post_launch_counters_activity_and_catalog_upgrade_preserve_history(pg):
    uid, lid, did = await seed(pg)
    await seed_catalog_games(pg)
    await launch(pg, [entry(target=999)])
    await tickets(pg, uid, lid, did, 100)
    base = datetime.now(UTC) + timedelta(days=1)
    for day in list(range(7)) + list(range(10, 17)):
        async with pg() as s, s.begin():
            await record_activity(s, uid, base + timedelta(days=day))
            await record_activity(s, uid, base + timedelta(days=day, minutes=1))
    await quiet(pg)
    async with pg() as s, s.begin():
        started = (await s.get(AchievementRuntime, 1)).started_at
        await import_catalog(s, uncommon_catalog())
    await quiet(pg)
    async with pg() as s:
        codes = set(
            await s.scalars(
                select(AchievementAward.code).where(AchievementAward.user_id == uid)
            )
        )
        assert {
            "uncommon_fifty_tickets",
            "uncommon_hundred_tickets",
            "uncommon_seven_day_streak",
            "uncommon_fourteen_days",
        } <= codes
        assert (await s.get(AchievementRuntime, 1)).started_at == started
        assert (await s.get(AchievementRuntime, 1)).projection_revision == 1
        days_before = await s.scalar(select(func.count()).select_from(AchievementDay))
    async with pg() as s, s.begin():
        await import_catalog(s, uncommon_catalog())  # no second initialization
    await quiet(pg)
    assert (await metrics(pg, uid))["paid_tickets"] == 100
    async with pg() as s:
        assert (
            await s.scalar(select(func.count()).select_from(AchievementDay))
            == days_before
        )
        assert await s.scalar(
            select(func.count()).select_from(AchievementAward)
        ) == len(codes)


@pytest.mark.asyncio
async def test_confirmed_results_award_exact_games_and_count_fifty_paid_wins(pg):
    uid, _, _ = await seed(pg)
    await seed_catalog_games(pg)
    await launch(pg, uncommon_catalog())
    fixtures = [
        ("flash", FAST_RULES, 3, 50),
        ("shadow", CODE_RULES, 3, 1),
        ("pulse", PULSE_RULES, 121, 1),
        ("september", SEPTEMBER_ECONOMY_RULES, 2, 1),
        ("pll", PLL_ECONOMY_RULES, 3, 1),
        ("bingo", BINGO_ECONOMY_RULES, 12, 1),
        ("khan", CLASSIC_ECONOMY_RULES, 3, 1),
        ("khan", CLASSIC_ECONOMY_RULES, 4, 1),
        ("pss", BALL_ECONOMY_RULES, 20, 1),
        ("weekly", GRAND_ECONOMY_RULES, 22, 1),
        ("dual", DUAL_ECONOMY_RULES, 11, 1),
    ]
    now = datetime.now(UTC)
    draw_time = now.replace(hour=12, minute=0, second=0)
    for i, (code, rules, match, count) in enumerate(fixtures):
        async with pg() as s, s.begin():
            lid = await s.scalar(select(Lottery.id).where(Lottery.code == code))
            d = Draw(
                id=uuid4(),
                lottery_id=lid,
                public_number=1000 + i,
                scheduled_at=draw_time + timedelta(minutes=i),
                sales_close_at=draw_time - timedelta(minutes=1),
                configuration_snapshot={"ruleset_code": rules.code, "ticket_price": 10},
            )
            s.add(d)
            did = d.id
        ids = await tickets(pg, uid, lid, did, count, start=1000 + i * 100)
        async with pg() as s, s.begin():
            await s.execute(
                update(Ticket)
                .where(Ticket.id.in_(ids))
                .values(
                    status="SETTLED",
                    matches=match,
                    prize_amount=100,
                    settled_at=now,
                    bingo_result={"moves": [18, 30, 40], "amounts": [30, 70, 0, 0]}
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
        expected = {e.code for e in uncommon_catalog()} - {
            "uncommon_ticket_warehouse",
            "uncommon_hundred_tickets",
            "uncommon_seven_day_streak",
            "uncommon_fourteen_days",
            "uncommon_three_daily_types",
        }
        assert expected <= codes
    m = await metrics(pg, uid)
    assert m["winning_tickets"] == 60 and m["winning_lotteries"] == 10
    assert m["prizes_count"] == 61  # one Bingo card, two prize components


@pytest.mark.asyncio
async def test_refund_event_retains_purchase_day_and_corrects_incomplete_progress(pg):
    uid, lid, did = await seed(pg)
    await launch(pg, [entry(metric="daily_play_types", target=3)])
    first = await tickets(pg, uid, lid, did, 1)
    async with pg() as s, s.begin():
        special_id = await s.scalar(
            select(Lottery.id).where(Lottery.code == "september")
        )
        d = Draw(
            id=uuid4(),
            lottery_id=special_id,
            public_number=900,
            scheduled_at=datetime.now(UTC) + timedelta(days=10),
            sales_close_at=datetime.now(UTC) + timedelta(days=9),
            configuration_snapshot={},
        )
        s.add(d)
        special_draw = d.id
    second = await tickets(pg, uid, special_id, special_draw, 1)
    await quiet(pg)
    assert (await metrics(pg, uid))["daily_play_types"] == 2
    async with pg() as s, s.begin():
        await s.execute(
            update(Ticket).where(Ticket.id.in_(second)).values(status="REFUNDED")
        )
    await quiet(pg)
    assert (await metrics(pg, uid))["daily_play_types"] == 1
    async with pg() as s:
        refund = await s.scalar(
            select(AchievementEvent).where(AchievementEvent.kind == "refund")
        )
        assert refund.payload["day"]
        assert await s.scalar(select(func.count()).select_from(AchievementAward)) == 0
        assert (await s.get(Ticket, first[0])).status == "PURCHASED"


async def open_gift_game(pg, code, *, cap=75, offset=1):
    rules = {"weekly": GRAND_ECONOMY_RULES, "bingo": BINGO_ECONOMY_RULES}[code]
    now = datetime.now(UTC)
    async with pg() as s, s.begin():
        game = await s.scalar(select(Lottery).where(Lottery.code == code))
        game.ruleset_code, game.numbers_to_pick, game.max_number = (
            rules.code,
            rules.numbers_to_pick,
            rules.max_number,
        )
        game.kind = LotteryKind.WEEKLY if code == "weekly" else LotteryKind.DAILY
        game.ticket_price, game.is_active = 50_000, True
        game.max_tickets_per_purchase = min(5, cap)
        game.max_tickets_per_user_per_draw = cap
        jackpot = await s.scalar(
            select(JackpotAccount).where(JackpotAccount.lottery_id == game.id)
        )
        d = Draw(
            id=uuid4(),
            lottery_id=game.id,
            public_number=100 + offset,
            scheduled_at=now + timedelta(days=offset),
            sales_close_at=now + timedelta(hours=offset),
            configuration_snapshot=draw_configuration_snapshot(
                game, jackpot.base_amount
            ),
        )
        s.add(d)
        return d.id


@pytest.mark.asyncio
@pytest.mark.parametrize("game", ["weekly", "bingo"])
async def test_grand_bingo_packs_conserve_funds_and_resume_without_duplicate(pg, game):
    uid, lid, did = await seed(pg)
    gift_draw = await open_gift_game(pg, game, cap=2)
    rewards = [
        {"type": "cas", "amount": 100_000},
        *[{"type": "ticket", "amount": 1, "lottery": game} for _ in range(3)],
        {"type": "case", "amount": 1, "planned": True},
    ]
    await launch(pg, [entry(target=1, rewards=rewards)])
    async with pg() as s:
        fund_before = (await s.get(KasperFundAccount, KASPER_FUND_ID)).balance
    await tickets(pg, uid, lid, did, 1)
    await quiet(pg)
    async with pg() as s:
        gifts = list(
            await s.scalars(select(Ticket).where(Ticket.source == TicketSource.GIFT))
        )
        assert len(gifts) == 2 and all(
            t.draw_id == gift_draw and t.purchase_price == 0 for t in gifts
        )
        assert (
            await s.get(KasperFundAccount, KASPER_FUND_ID)
        ).balance == fund_before - 200_000
        assert (await s.get(Balance, uid)).amount == 1_100_000
        award = await s.scalar(select(AchievementAward))
        award_id = award.id
        assert award.reward_status == "waiting"
        if game == "bingo":
            assert (
                await s.scalar(
                    select(func.count())
                    .select_from(BingoPoolTicket)
                    .where(BingoPoolTicket.ticket_id.in_([t.id for t in gifts]))
                )
                == 2
            )
    second = await open_gift_game(pg, game, cap=2, offset=2)
    async with pg() as s, s.begin():
        await s.execute(
            update(AchievementReward)
            .where(AchievementReward.status == "waiting")
            .values(retry_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    await quiet(pg)

    async def replay():
        async with pg() as s, s.begin():
            await execute_rewards(s, award_id, datetime.now(UTC))

    await asyncio.gather(*(replay() for _ in range(3)))
    async with pg() as s:
        gifts = list(
            await s.scalars(select(Ticket).where(Ticket.source == TicketSource.GIFT))
        )
        assert len(gifts) == 3 and len({t.achievement_reward_id for t in gifts}) == 3
        assert sum(t.draw_id == second for t in gifts) == 1
        assert (
            await s.get(KasperFundAccount, KASPER_FUND_ID)
        ).balance == fund_before - 250_000
        assert (await s.get(AchievementAward, award_id)).reward_status == "planned"
        assert len(gifts[0].numbers) == (12 if game == "bingo" else 7)
    m = await metrics(pg, uid)
    assert m["paid_tickets"] == 1 and m["gift_tickets"] == 3
