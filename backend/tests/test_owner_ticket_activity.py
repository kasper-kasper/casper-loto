"""Actual PostgreSQL: owner ticket counts match purchases, not draws or gifts."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import insert, select

from k_loto.application.achievement_catalog import import_catalog
from k_loto.application.owner_economy import ticket_activity_query
from k_loto.domain.enums import TicketSource, TicketStatus
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementReward,
)
from k_loto.infrastructure.database.models import (
    Draw,
    InstantTicket,
    Lottery,
    Ticket,
    User,
)
from test_achievements import entry, seed
from test_achievements import pg as pg


async def test_moscow_purchase_window_types_gifts_refunds_epoch_and_unique_buyers(pg):
    uid, lid, did = await seed(pg)
    fast_uid, fast_lid, fast_did = await seed(pg)
    start = datetime(2026, 10, 19, 21, tzinfo=UTC)  # 20 October, 00:00 Moscow
    end = start + timedelta(days=1)
    gift_uid, reward_id, award_id = uuid4(), uuid4(), uuid4()
    async with pg() as session, session.begin():
        fast_lid = await session.scalar(
            select(Lottery.id).where(Lottery.code == "flash")
        )
        fast_draw = await session.get(Draw, fast_did)
        fast_draw.lottery_id = fast_lid
        fast_draw.public_number = 9_000_000
        session.add(User(id=gift_uid, display_name="Only receives gifts"))
        await import_catalog(session, [entry()])
        session.add(
            AchievementAward(
                id=award_id,
                user_id=gift_uid,
                code="test-purchase",
                version=1,
                rarity="common",
                snapshot={},
                earned_at=start,
                event_key="fixture",
            )
        )
        await session.flush()
        session.add(
            AchievementReward(id=reward_id, award_id=award_id, position=0, payload={})
        )
        await session.flush()
        base = dict(numbers=[1, 2, 3, 4, 5], purchase_price=10, purchased_at=start)
        regular = [
            dict(
                base,
                id=uuid4(),
                user_id=uid,
                lottery_id=lid,
                draw_id=did,
                public_number=n,
                purchased_at=stamp,
            )
            for n, stamp in enumerate(
                (
                    start,
                    end - timedelta(microseconds=1),
                    end,
                    start - timedelta(microseconds=1),
                ),
                1,
            )
        ]
        # A ticket associated with two draws is still a single purchase.
        regular[0]["second_draw_id"] = fast_did
        for row in regular:
            await session.execute(insert(Ticket).values(**row))
        for number in (1, 2):
            await session.execute(
                insert(Ticket).values(
                    **base,
                    id=uuid4(),
                    user_id=fast_uid,
                    lottery_id=fast_lid,
                    draw_id=fast_did,
                    public_number=number,
                    status=TicketStatus.REFUNDED
                    if number == 2
                    else TicketStatus.SETTLED,
                )
            )
        await session.execute(
            insert(Ticket).values(
                **{**base, "purchase_price": 0},
                id=uuid4(),
                user_id=gift_uid,
                lottery_id=lid,
                draw_id=did,
                public_number=5,
                source=TicketSource.GIFT,
                selection_mode="random",
                achievement_reward_id=reward_id,
            )
        )
        old_draw = Draw(
            id=uuid4(),
            lottery_id=lid,
            public_number=2,
            scheduled_at=end,
            sales_close_at=start,
            configuration_snapshot={"economy_epoch": 2},
        )
        session.add(old_draw)
        await session.flush()
        await session.execute(
            insert(Ticket).values(
                **base,
                id=uuid4(),
                user_id=uid,
                lottery_id=lid,
                draw_id=old_draw.id,
                public_number=6,
            )
        )
        for stamp in (start, end - timedelta(microseconds=1), end):
            session.add(
                InstantTicket(
                    user_id=uid,
                    symbols=[1, 1, 1],
                    purchase_price=10,
                    prize_amount=0,
                    odds_version="fixture",
                    purchased_at=stamp,
                )
            )
    async with pg() as session:
        result = (
            (
                await session.execute(
                    ticket_activity_query(start=start, end=end, epoch=1)
                )
            )
            .mappings()
            .one()
        )
        assert dict(result) == {
            "regular": 2,
            "fast": 2,
            "instant": 2,
            "gift": 1,
            "refunded": 1,
            "buyers": 2,
        }
