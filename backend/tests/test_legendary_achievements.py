"""Jackpot provenance, fixed meta collection, deferred large gifts and cosmetics."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError

from k_loto.api.dependencies import (
    CurrentMiniAppUser,
    get_current_miniapp_user,
    get_db_session,
)
from k_loto.application.achievement_catalog import CatalogEntry, import_catalog
from k_loto.application.achievement_results import ticket_result
from k_loto.application.achievements import execute_rewards
from k_loto.application.collection import choose_cosmetics, read_collection
from k_loto.application.legendary_achievements import (
    LEGENDARY_CODES,
    MASTER_CODE,
    legendary_catalog,
)
from k_loto.domain.achievement_gifts import combination_count, gift_draw_capacity
from k_loto.domain.achievements import Condition
from k_loto.domain.lottery_rules import (
    BINGO_ECONOMY_RULES,
    CODE_RULES,
    FAST_RULES,
    PULSE_RULES,
)
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementReward,
    CollectionUnlock,
)
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    Lottery,
    Ticket,
    TicketSource,
)
from k_loto.main import create_app
from test_achievements import entry, launch, metrics, quiet, seed, tickets
from test_achievements import pg as pg
from test_common_achievements import seed_catalog_games
from test_uncommon_achievements import open_gift_game


def test_catalog_owner_ranges_fixed_collection_and_300_per_game():
    entries = legendary_catalog()
    assert len(entries) == len({e.code for e in entries}) == 11
    for e in entries[:-1]:
        rewards = {r.type: r for r in e.rewards}
        assert rewards["cas"].amount >= 40_000_000
        assert 100 <= rewards["ticket_pack"].amount <= 500
        assert rewards["ticket_pack"].lottery == e.condition.conditions[0].lottery
        assert 20 <= rewards["case"].amount <= 100 and rewards["case"].planned
        assert e.condition.conditions[0].natural_jackpot
    final = entries[-1]
    assert final.code == MASTER_CODE and final.title == "Каспер, подвинься"
    assert final.condition.conditions[0].achievement_codes == list(LEGENDARY_CODES)
    assert final.condition.conditions[0].target == 10
    assert sum(r.amount for r in final.rewards if r.type == "cas") == 1_000_000_000
    assert (
        len([r for r in final.rewards if r.type == "ticket_pack" and r.amount == 300])
        == 10
    )
    assert all(r.lottery != "dual" for e in entries for r in e.rewards)
    assert next(r.amount for r in final.rewards if r.type == "case") == 200
    assert all(len(e.rewards) <= 16 for e in entries)


@pytest.mark.parametrize(
    "game,rules,match,moves,distribution,accepted",
    [
        ("flash", FAST_RULES, 5, None, False, True),
        ("flash", FAST_RULES, 4, None, False, False),
        ("shadow", CODE_RULES, 5, None, False, True),
        ("shadow", CODE_RULES, 4, None, False, False),
        ("pulse", PULSE_RULES, 221, None, False, True),
        ("pulse", PULSE_RULES, 220, None, False, False),
        ("bingo", BINGO_ECONOMY_RULES, 12, [15, 25, 28], False, True),
        ("bingo", BINGO_ECONOMY_RULES, 12, [15, 25, 29], False, False),
        ("bingo", BINGO_ECONOMY_RULES, 12, [15, 25, 28], True, False),
    ],
)
def test_genuine_jackpot_boundaries(game, rules, match, moves, distribution, accepted):
    c = next(
        e for e in legendary_catalog() if e.code == f"legendary_{game}_jackpot"
    ).condition.conditions[0]
    result = ticket_result(
        SimpleNamespace(
            matches=match,
            prize_amount=1,
            purchase_price=10,
            bingo_result={"moves": moves, "amounts": [0, 0, 1, 0]} if moves else None,
        ),
        SimpleNamespace(
            configuration_snapshot={"ruleset_code": rules.code},
            is_distribution=distribution,
        ),
        SimpleNamespace(code=game, ruleset_code=rules.code),
    )
    assert c.matches_result(result) is accepted


def test_combinations_and_gift_cap_never_cover_every_outcome():
    from k_loto.domain.lottery_rules import GRAND_ECONOMY_RULES, PLL_ECONOMY_RULES

    assert combination_count(GRAND_ECONOMY_RULES.code) == 3_246_320
    assert combination_count(PLL_ECONOMY_RULES.code) == 1365
    assert (
        gift_draw_capacity(
            SimpleNamespace(
                code="pll",
                ruleset_code=PLL_ECONOMY_RULES.code,
                max_tickets_per_user_per_draw=5000,
            )
        )
        == 1364
    )
    assert (
        gift_draw_capacity(
            SimpleNamespace(
                code="bingo",
                ruleset_code=BINGO_ECONOMY_RULES.code,
                max_tickets_per_user_per_draw=75,
            )
        )
        == 75
    )


@pytest.mark.parametrize("codes,target", [(["x", "x"], 2), ([], 0), (["x"], 2)])
def test_invalid_meta_sets(codes, target):
    with pytest.raises(ValidationError):
        Condition(metric="earned_set", achievement_codes=codes, target=target)


@pytest.mark.asyncio
async def test_meta_rejects_cycle_and_unknown_dependency(pg):
    await seed(pg)
    await launch(pg, [])
    for codes in [["cycle"], ["missing"]]:
        with pytest.raises(ValueError, match="cyclic"):
            async with pg() as s, s.begin():
                await import_catalog(
                    s,
                    [
                        CatalogEntry.model_validate(
                            dict(
                                code="cycle",
                                version=1,
                                title="Fixture",
                                description="",
                                rarity="legendary",
                                active=True,
                                condition={
                                    "conditions": [
                                        dict(
                                            metric="earned_set",
                                            target=1,
                                            achievement_codes=codes,
                                        )
                                    ]
                                },
                            )
                        )
                    ],
                )


async def retry_due(pg):
    async with pg() as s, s.begin():
        await s.execute(
            update(AchievementReward)
            .where(AchievementReward.status == "waiting")
            .values(retry_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    await quiet(pg)


@pytest.mark.asyncio
@pytest.mark.parametrize("game", ["weekly", "bingo"])
async def test_pack_splits_at_cap_survives_parallel_replay_and_never_counts_as_paid(
    pg, game
):
    uid, lid, did = await seed(pg)
    first = await open_gift_game(pg, game, cap=2)
    await launch(
        pg,
        [
            entry(
                target=1,
                rewards=[
                    dict(type="ticket_pack", amount=5, lottery=game),
                    dict(type="case", amount=200, planned=True),
                ],
            )
        ],
    )
    await tickets(pg, uid, lid, did, 1)
    await quiet(pg)
    for _ in range(2):
        await retry_due(pg)
    async with pg() as s:
        award = await s.scalar(select(AchievementAward))
        award_id = award.id
        assert (
            await s.scalar(
                select(func.count())
                .select_from(Ticket)
                .where(Ticket.source == TicketSource.GIFT)
            )
            == 2
        )
    await open_gift_game(pg, game, cap=2, offset=2)
    for _ in range(3):
        await retry_due(pg)
    await open_gift_game(pg, game, cap=2, offset=3)
    for _ in range(2):
        await retry_due(pg)

    async def replay():
        async with pg() as s, s.begin():
            await execute_rewards(s, award_id, datetime.now(UTC))

    await asyncio.gather(*(replay() for _ in range(3)))
    async with pg() as s:
        gifts = list(
            await s.scalars(select(Ticket).where(Ticket.source == TicketSource.GIFT))
        )
        assert len(gifts) == len({t.achievement_reward_id for t in gifts}) == 5
        assert sum(t.draw_id == first for t in gifts) == 2
        parent = await s.scalar(
            select(AchievementReward).where(
                AchievementReward.award_id == award_id,
                AchievementReward.parent_id.is_(None),
                AchievementReward.payload["type"].astext == "ticket_pack",
            )
        )
        assert parent.completed_units == 5 and parent.status == "completed"
        assert (await s.get(AchievementAward, award_id)).reward_status == "planned"
        assert (
            await s.scalar(
                select(func.count())
                .select_from(AchievementReward)
                .where(AchievementReward.parent_id == parent.id)
            )
            == 5
        )
    m = await metrics(pg, uid)
    assert m["paid_tickets"] == 1 and m["gift_tickets"] == 5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "game,rules",
    [("flash", FAST_RULES), ("shadow", CODE_RULES), ("pulse", PULSE_RULES)],
)
async def test_real_fast_gift_uses_standard_payment_and_combination_rules(
    pg, game, rules
):
    uid, lid, did = await seed(pg)
    await seed_catalog_games(pg)
    now = datetime.now(UTC)
    async with pg() as s, s.begin():
        g = await s.scalar(select(Lottery).where(Lottery.code == game))
        g.ruleset_code = rules.code
        g.numbers_to_pick, g.max_number = rules.numbers_to_pick, rules.max_number
        g.ticket_price = 2000
        target = Draw(
            id=uuid4(),
            lottery_id=g.id,
            public_number=900,
            scheduled_at=now + timedelta(hours=1),
            sales_close_at=now + timedelta(minutes=50),
            configuration_snapshot={
                "ruleset_code": rules.code,
                "ticket_price": 2000,
                "max_tickets_per_user_per_draw": 500,
                "max_tickets_per_purchase": 100,
            },
        )
        s.add(target)
    await launch(
        pg,
        [entry(target=1, rewards=[dict(type="ticket_pack", amount=2, lottery=game)])],
    )
    await tickets(pg, uid, lid, did, 1)
    await quiet(pg)
    await retry_due(pg)
    async with pg() as s:
        gifts = list(
            await s.scalars(select(Ticket).where(Ticket.source == TicketSource.GIFT))
        )
        assert len(gifts) == 2
        assert all(t.purchase_price == 0 for t in gifts)
        if game == "shadow":
            assert all(
                len(t.numbers) == 5 and all(0 <= n <= 9 for n in t.numbers)
                for t in gifts
            )
        if game == "pulse":
            assert all(
                len(t.numbers) == 5 and 1001 <= t.numbers[-1] <= 1199 for t in gifts
            )


@pytest.mark.asyncio
async def test_all_ten_source_jackpots_award_final_once_and_persistent_cosmetics(pg):
    from k_loto.domain.lottery_rules import (
        BALL_ECONOMY_RULES,
        CLASSIC_ECONOMY_RULES,
        GRAND_ECONOMY_RULES,
        HALLOWEEN_ECONOMY_RULES,
        PLL_ECONOMY_RULES,
        SEPTEMBER_ECONOMY_RULES,
    )

    actual_rules = {
        "flash": FAST_RULES,
        "shadow": CODE_RULES,
        "pulse": PULSE_RULES,
        "khan": CLASSIC_ECONOMY_RULES,
        "pss": BALL_ECONOMY_RULES,
        "weekly": GRAND_ECONOMY_RULES,
        "bingo": BINGO_ECONOMY_RULES,
        "pll": PLL_ECONOMY_RULES,
        "grob": HALLOWEEN_ECONOMY_RULES,
        "september": SEPTEMBER_ECONOMY_RULES,
    }

    uid, _, _ = await seed(pg)
    await seed_catalog_games(pg)
    # Keep approved CAS/cosmetics/cases; gift purchases have their own tests.
    entries = [
        e.model_copy(
            update={"rewards": [r for r in e.rewards if r.type != "ticket_pack"]}
        )
        for e in legendary_catalog()
    ]
    await launch(pg, entries)
    now = datetime.now(UTC)
    async with pg() as s:
        games = {
            g.code: (g.id, g.ruleset_code) for g in await s.scalars(select(Lottery))
        }
    for i, e in enumerate(entries[:-1]):
        game = e.condition.conditions[0].lottery
        gid, _ = games[game]
        # Test each current game's frozen format, independent of template versions.
        rules = actual_rules[game]
        ruleset = rules.code
        async with pg() as s, s.begin():
            d = Draw(
                id=uuid4(),
                lottery_id=gid,
                public_number=10000 + i,
                scheduled_at=now + timedelta(minutes=i),
                sales_close_at=now,
                configuration_snapshot={"ruleset_code": ruleset, "ticket_price": 10},
            )
            s.add(d)
            draw_id = d.id
        ids = await tickets(pg, uid, gid, draw_id, 1, start=10000)
        async with pg() as s, s.begin():
            await s.execute(
                update(Ticket)
                .where(Ticket.id == ids[0])
                .values(
                    status="SETTLED",
                    matches=rules.jackpot_match,
                    prize_amount=10_000,
                    settled_at=now,
                    bingo_result={"moves": [10, 20, 28], "amounts": [0, 0, 10000, 0]}
                    if game == "bingo"
                    else None,
                )
            )
            await s.execute(
                update(Draw)
                .where(Draw.id == draw_id)
                .values(status="COMPLETED", executed_at=now)
            )
        await quiet(pg)
        async with pg() as s:
            codes = set(await s.scalars(select(AchievementAward.code)))
            assert (MASTER_CODE in codes) == (i == 9)
    async with pg() as s:
        final = await s.scalar(
            select(AchievementAward).where(AchievementAward.code == MASTER_CODE)
        )
        final_id = final.id
        assert (await s.get(Balance, uid)).amount == 1_001_000_000 + sum(
            next(r.amount for r in e.rewards if r.type == "cas") for e in entries[:-1]
        )
        collection = await read_collection(s, uid)
        assert collection["active_theme"] is None and collection["active_badge"] is None
        assert sum(item["unlocked"] for item in collection["items"]) == 13
    for _ in range(2):
        async with pg() as s, s.begin():
            await execute_rewards(s, final_id, now)
    async with pg() as s, s.begin():
        await choose_cosmetics(
            s, uid, badge="badge:casper-master", theme="theme:beyond"
        )
    async with pg() as s:
        assert (await read_collection(s, uid))["active_theme"] == "theme:beyond"
        assert (
            await s.scalar(
                select(func.count())
                .select_from(CollectionUnlock)
                .where(
                    CollectionUnlock.user_id == uid,
                    CollectionUnlock.item == "theme:gold",
                )
            )
            == 1
        )
    async with pg() as s, s.begin():
        await choose_cosmetics(s, uid, badge=None, theme=None)
    other, _, _ = await seed(pg)
    with pytest.raises(ValueError, match="unlocked"):
        async with pg() as s, s.begin():
            await choose_cosmetics(s, other, badge="badge:casper-master", theme=None)
    with pytest.raises(DBAPIError):
        async with pg() as s, s.begin():
            await s.execute(
                update(CollectionUnlock)
                .where(CollectionUnlock.user_id == uid)
                .values(item="forged")
            )


@pytest.mark.asyncio
async def test_collection_http_ownership_locked_selection_reset_and_no_client_grants(
    pg,
):
    uid, lid, did = await seed(pg)
    await launch(
        pg,
        [
            entry(
                target=1,
                rewards=[
                    dict(type="cosmetic", item="badge:flash"),
                    dict(type="cosmetic", item="theme:gold"),
                ],
            )
        ],
    )
    app = create_app()

    async def identity():
        return CurrentMiniAppUser(uid, 123)

    async def session():
        async with pg() as s:
            yield s

    app.dependency_overrides[get_current_miniapp_user] = identity
    app.dependency_overrides[get_db_session] = session
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://test"
    ) as client:
        url = "/api/v1/miniapp/achievements/collection"
        response = await client.get(url)
        assert response.status_code == 200 and not any(
            i["unlocked"] for i in response.json()["items"]
        )
        assert (
            await client.put(url, json={"badge": "badge:flash", "theme": None})
        ).status_code == 400
        assert (
            await client.put(
                url, json={"badge": None, "theme": None, "cas": 1_000_000_000}
            )
        ).status_code == 422
        await tickets(pg, uid, lid, did, 1)
        await quiet(pg)
        response = await client.put(
            url, json={"badge": "badge:flash", "theme": "theme:gold"}
        )
        assert (
            response.status_code == 200
            and response.json()["active_theme"] == "theme:gold"
        )
        assert (
            await client.put(url, json={"badge": "theme:gold", "theme": None})
        ).status_code == 400
        assert (
            await client.put(url, json={"badge": None, "theme": None})
        ).status_code == 200
        assert (await client.get(url)).json()["active_badge"] is None
    async with pg() as s:
        assert (await s.get(Balance, uid)).amount == 1_000_000
