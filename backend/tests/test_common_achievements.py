"""Approved catalog, real purchase provenance, settlement and read-side contracts."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update

from k_loto.api.dependencies import (
    CurrentMiniAppUser,
    get_current_miniapp_user,
    get_db_session,
)
from k_loto.application.achievements import drain, record_activity
from k_loto.application.common_achievements import common_catalog
from k_loto.application.weekly import LotteryTicketPurchaseService
from k_loto.domain.achievements import Condition
from k_loto.domain.enums import DrawStatus, TicketStatus
from k_loto.domain.instant import instant_rules
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementEvent,
    AchievementPlayer,
)
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    InstantTicket,
    JackpotAccount,
    LedgerTransaction,
    Lottery,
    Ticket,
)
from k_loto.main import create_app
from test_achievements import entry, launch, metrics, quiet, seed, tickets
from test_achievements import pg as pg


@pytest.mark.asyncio
async def test_pg_refund_timing_does_not_change_completed_purchase_milestones(pg):
    players = [await seed(pg), await seed(pg)]
    await launch(
        pg,
        [
            entry(code="first_ticket", target=1),
            entry(code="bulk_purchase", metric="bulk_purchases", target=1),
        ],
    )

    async def purchase_and_refund(player, process_first):
        uid, lid, did = player
        operation = uuid4()
        async with pg() as s, s.begin():
            s.add_all(
                [
                    Ticket(
                        id=uuid4(),
                        user_id=uid,
                        lottery_id=lid,
                        draw_id=did,
                        public_number=n,
                        numbers=[1, 2, 3, 4, 5],
                        purchase_price=10,
                        purchase_operation_id=operation,
                    )
                    for n in range(1, 6)
                ]
            )
        if process_first:
            await quiet(pg)
        async with pg() as s, s.begin():
            await s.execute(
                update(Ticket)
                .where(Ticket.purchase_operation_id == operation)
                .values(status=TicketStatus.REFUNDED)
            )
        await quiet(pg)
        assert (await metrics(pg, uid))["paid_tickets"] == 0
        async with pg() as s:
            return set(
                await s.scalars(
                    select(AchievementAward.code).where(AchievementAward.user_id == uid)
                )
            )

    assert await purchase_and_refund(players[0], True) == {
        "first_ticket",
        "bulk_purchase",
    }
    assert await purchase_and_refund(players[1], False) == {
        "first_ticket",
        "bulk_purchase",
    }


@pytest.mark.asyncio
async def test_pg_game_groups_distinct_games_25_tickets_and_moscow_openings(pg):
    uid, _, _ = await seed(pg)
    await seed_catalog_games(pg)
    await launch(pg, common_catalog())
    now = datetime.now(UTC)
    for index, code in enumerate(
        ["flash", "september", "khan", "pss", "weekly", "dual", "bingo"]
    ):
        did = uuid4()
        async with pg() as s, s.begin():
            lid = await s.scalar(select(Lottery.id).where(Lottery.code == code))
            s.add(
                Draw(
                    id=did,
                    lottery_id=lid,
                    public_number=100000 + index,
                    status=DrawStatus.SCHEDULED,
                    scheduled_at=now + timedelta(days=3),
                    sales_close_at=now + timedelta(days=2),
                    configuration_snapshot={},
                )
            )
        await tickets(pg, uid, lid, did, 19 if index == 0 else 1, start=100000)
    async with pg() as s, s.begin():
        rules = instant_rules("aurora")
        s.add(
            InstantTicket(
                id=uuid4(),
                user_id=uid,
                symbols=[1, 2, 3],
                purchase_price=rules.price,
                prize_amount=0,
                odds_version=rules.version,
            )
        )
        base = now.replace(hour=20, minute=59, second=0)
        for moment in (
            base,
            base + timedelta(minutes=2),
            base + timedelta(minutes=3),
            base + timedelta(days=1, minutes=2),
        ):
            await record_activity(s, uid, moment)
    await quiet(pg)
    m = await metrics(pg, uid)
    assert m["paid_tickets"] == 26 and m["lotteries_count"] == 8
    assert m["active_days"] == 3
    async with pg() as s:
        codes = set(await s.scalars(select(AchievementAward.code)))
        assert codes >= {
            "first_ticket",
            "ten_tickets",
            "twenty_five_tickets",
            "three_games",
            "seven_games",
            "first_fast",
            "first_instant",
            "first_custom",
            "first_classic",
            "first_ball",
            "first_grand",
            "first_dual",
            "first_bingo",
            "three_days",
        }
        assert "own_combination" not in codes and "bulk_purchase" not in codes


def test_approved_catalog_is_exactly_22_funded_common_entries():
    catalog = common_catalog()
    assert len(catalog) == len({c.code for c in catalog}) == 22
    assert {c.rarity for c in catalog} == {"common"}
    assert all(
        c.active and c.visible and not c.reward_pending and c.rewards for c in catalog
    )
    rewards = [r for c in catalog for r in c.rewards]
    assert sum(r.amount for r in rewards if r.type == "cas") == 930_000
    assert sum(r.amount for r in rewards if r.type == "ticket") == 8
    assert sum(r.amount for r in rewards if r.type == "case" and r.planned) == 4
    custom = next(c for c in catalog if c.code == "first_custom")
    assert {c.lottery for c in custom.condition.conditions} == {
        "september",
        "pll",
        "grob",
    }
    assert (
        next(c for c in catalog if c.code == "first_grand")
        .condition.conditions[0]
        .lottery
        == "weekly"
    )


@pytest.mark.parametrize(
    "payout,equals,profit",
    [(0, False, False), (9, False, False), (10, True, False), (11, False, True)],
)
def test_payout_comparison_uses_paid_price(payout, equals, profit):
    result = {
        "prize": payout,
        "paid": 10,
        "standard_price": 50,
        "lottery": "bingo",
        "matches": 0,
        "categories": [],
    }
    assert (
        Condition(
            metric="qualifying_wins", target=1, payout_vs_price="eq"
        ).matches_result(result)
        is equals
    )
    assert (
        Condition(
            metric="qualifying_wins", target=1, payout_vs_price="gt"
        ).matches_result(result)
        is profit
    )


async def seed_catalog_games(factory):
    async with factory() as s, s.begin():
        existing = set(await s.scalars(select(Lottery.code)))
        for code in (
            {
                c.lottery
                for e in common_catalog()
                for c in e.condition.conditions
                if c.lottery
            }
            - {"kasper-live", "aurora", "vault"}
            - existing
        ):
            s.add(
                Lottery(
                    id=uuid4(),
                    code=code,
                    name=code,
                    kind="WEEKLY",
                    ruleset_code="weekly_5_20",
                    numbers_to_pick=5,
                    max_number=20,
                    ticket_price=100,
                    sales_cutoff_minutes=5,
                    schedule={},
                )
            )


@pytest.mark.asyncio
async def test_pg_common_catalog_real_purchase_manual_bulk_refunds_and_funded_rewards(
    pg,
):
    uid, lid, did = await seed(pg)
    await seed_catalog_games(pg)
    async with pg() as s, s.begin():
        lottery = await s.get(Lottery, lid)
        lottery.is_active, lottery.ticket_price = True, 100
        code = lottery.code
        draw = await s.get(Draw, did)
        draw.configuration_snapshot = {
            "ruleset_code": "weekly_5_20",
            "ticket_price": 100,
        }
        s.add(
            JackpotAccount(id=uuid4(), lottery_id=lid, balance=10000, base_amount=10000)
        )
    await launch(pg, common_catalog())

    async def buy(count, mode):
        async with pg() as s:
            return await LotteryTicketPurchaseService(
                s, lottery_code=code, target_draw_id=did
            ).purchase(
                user_id=uid,
                combinations=[[1, 2, 3, 4, 5]] * count,
                selection_modes=[mode] * count,
                idempotency_key=str(uuid4()),
            )

    # Four separate purchases cannot satisfy the bulk condition.
    for _ in range(4):
        await buy(1, "random")
    await quiet(pg)
    async with pg() as s:
        assert set(await s.scalars(select(AchievementAward.code))) == {
            "first_ticket",
            "first_achievement_reward",
        }
    bulk = await buy(5, "manual")
    await asyncio.gather(*(drain(pg, limit=30) for _ in range(3)))
    await quiet(pg)
    async with pg() as s:
        awards = list(await s.scalars(select(AchievementAward)))
        assert {a.code for a in awards} == {
            "first_ticket",
            "own_combination",
            "bulk_purchase",
            "first_achievement_reward",
        }
        assert all(a.reward_status in {"completed", "waiting"} for a in awards)
        assert (await s.get(Balance, uid)).amount == 1_114_100
        assert (
            await s.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(LedgerTransaction.type == "ACHIEVEMENT_REWARD")
            )
            == 8
        )
        assert all(
            t.selection_mode == "manual"
            for t in await s.scalars(
                select(Ticket).where(Ticket.id.in_(bulk.ticket_ids))
            )
        )
    # Synthetic fixture; the refund service owns compensating ledger movements.
    async with pg() as s, s.begin():
        await s.execute(
            update(Ticket)
            .where(Ticket.id.in_(bulk.ticket_ids))
            .values(status=TicketStatus.REFUNDED)
        )
    await quiet(pg)
    m = await metrics(pg, uid)
    assert m["paid_tickets"] == 4 and m["manual_tickets"] == 0
    await buy(1, "random")
    await quiet(pg)
    async with pg() as s:
        assert await s.scalar(select(func.count()).select_from(AchievementAward)) == 4


@pytest.mark.asyncio
async def test_pg_old_tickets_excluded_and_bingo_components_are_one_win(pg):
    uid, lid, did = await seed(pg)
    await seed_catalog_games(pg)
    old = await tickets(pg, uid, lid, did, 1)
    await launch(pg, common_catalog())
    new = await tickets(pg, uid, lid, did, 10, start=2)
    async with pg() as s, s.begin():
        await s.execute(
            update(Ticket)
            .where(Ticket.id.in_(old + new[1:]))
            .values(
                status=TicketStatus.SETTLED,
                matches=3,
                prize_amount=10,
                settled_at=datetime.now(UTC),
            )
        )
        await s.execute(
            update(Ticket)
            .where(Ticket.id == new[0])
            .values(
                status=TicketStatus.SETTLED,
                matches=3,
                prize_amount=11,
                settled_at=datetime.now(UTC),
                bingo_result={"amounts": [3, 8, 0]},
            )
        )
        await s.execute(
            update(Draw)
            .where(Draw.id == did)
            .values(status=DrawStatus.COMPLETED, executed_at=datetime.now(UTC))
        )
    await quiet(pg)
    m = await metrics(pg, uid)
    assert m["winning_tickets"] == 10 and m["prizes_count"] == 11
    async with pg() as s:
        assert set(await s.scalars(select(AchievementAward.code))) >= {
            "first_ticket",
            "ten_tickets",
            "first_win",
            "break_even",
            "first_profit",
            "five_wins",
            "ten_wins",
        }
        assert "first_achievement_reward" in set(
            await s.scalars(select(AchievementAward.code))
        )


@pytest.mark.asyncio
async def test_pg_reward_meta_cannot_recurse_and_duplicate_events_are_noops(pg):
    uid, lid, did = await seed(pg)
    meta = next(c for c in common_catalog() if c.code == "first_achievement_reward")
    meta.reward_pending = False
    from k_loto.domain.achievements import RewardSpec

    meta.rewards = [RewardSpec(type="cas", amount=7)]
    await launch(pg, [entry(target=1, rewards=[{"type": "cas", "amount": 13}]), meta])
    await tickets(pg, uid, lid, did, 1)
    await quiet(pg)
    async with pg() as s:
        assert (await s.get(Balance, uid)).amount == 1000020
        assert await s.scalar(select(func.count()).select_from(AchievementAward)) == 2
        assert (await s.get(AchievementPlayer, uid)).metrics[
            "rewarded_achievements"
        ] == 1
        assert (
            await s.scalar(
                select(func.count())
                .select_from(AchievementEvent)
                .where(AchievementEvent.kind == "reward_paid")
            )
            == 1
        )
    await asyncio.gather(*(drain(pg, limit=20) for _ in range(3)))
    async with pg() as s:
        assert (await s.get(Balance, uid)).amount == 1000020


@pytest.mark.asyncio
async def test_pg_api_sort_filter_page_secret_and_reads_never_award(pg):
    uid, lid, did = await seed(pg)
    definitions = [
        entry(code="one", target=1),
        entry(code="ten", target=10),
        entry(code="twenty", target=20),
        entry(code="hidden", target=50, secret=True),
    ]
    await launch(pg, definitions)
    await tickets(pg, uid, lid, did, 7)
    await quiet(pg)
    app = create_app()

    async def db():
        async with pg() as s:
            yield s

    app.dependency_overrides[get_db_session] = db
    app.dependency_overrides[get_current_miniapp_user] = lambda: CurrentMiniAppUser(
        id=uid, telegram_id=1
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        path = "/api/v1/miniapp/achievements"
        body = (await client.get(path, params={"limit": 2})).json()
        assert [i["code"] for i in body["items"]] == ["one", "ten"]
        assert body["next_offset"] == 2 and body["total"] == 4
        locked = (await client.get(path, params={"status": "locked"})).json()
        assert [i["code"] for i in locked["items"]] == ["ten", "twenty", "hidden"]
        assert (
            "description" not in locked["items"][-1]
            and "progress" not in locked["items"][-1]
        )
        assert (
            len((await client.get(path, params={"category": "secret"})).json()["items"])
            == 1
        )
        assert (
            len((await client.get(path, params={"summary": True})).json()["items"]) == 1
        )
        assert (
            await client.get(path, params={"category": "invented"})
        ).status_code == 422
        notices = (await client.get(path + "/unseen")).json()
        assert len(notices) == 1
        assert (
            await client.post(
                path + "/seen", json={"ids": [notices[0]["notification_id"]]}
            )
        ).status_code == 204
        assert (await client.get(path + "/unseen")).json() == []
    async with pg() as s:
        assert await s.scalar(select(func.count()).select_from(AchievementAward)) == 1
    app.dependency_overrides.clear()
