"""Transactional profile regressions on disposable synthetic data only."""

# ruff: noqa: E501 -- SQL fixtures and independent assertions.

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import insert, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from k_loto.application.miniapp import MiniAppQueryService
from k_loto.application.profile_projection import ProfileProjectionService
from k_loto.domain.enums import (
    DrawStatus,
    InAppNotificationType,
    LotteryKind,
    TicketStatus,
)
from k_loto.infrastructure.database.models import (
    Draw,
    InstantTicket,
    Lottery,
    PlayerProfileStats,
    Ticket,
    User,
    UserNotification,
)
from k_loto.infrastructure.database.session import engine, session_factory


async def consistent() -> None:
    async with session_factory() as session:
        check = await ProfileProjectionService(session).verify()
        assert check.profiles == check.lotteries == 0, check


async def main() -> None:
    if not str(engine.url.database).startswith("k_loto_audit_stage1_"):
        raise RuntimeError("Disposable synthetic audit database required")
    await consistent()
    now = datetime.now(UTC)
    uid, other, lid, did = (uuid4() for _ in range(4))
    async with session_factory() as session, session.begin():
        session.add_all(
            [
                User(id=uid, display_name="Profile smoke"),
                User(id=other, display_name="Empty profile"),
            ]
        )
        session.add(
            Lottery(
                id=lid,
                code="profile-smoke",
                name="Profile smoke",
                kind=LotteryKind.WEEKLY,
                ruleset_code="weekly_5_20",
                numbers_to_pick=5,
                max_number=20,
                ticket_price=100,
                sales_cutoff_minutes=5,
                schedule={},
            )
        )
        await session.flush()
        session.add(
            Draw(
                id=did,
                lottery_id=lid,
                public_number=1,
                status=DrawStatus.SCHEDULED,
                scheduled_at=now + timedelta(days=10),
                sales_close_at=now + timedelta(days=9),
                correlation_id=uuid4(),
            )
        )
        await session.flush()
        empty = await MiniAppQueryService(session).account(other)
        assert (
            empty.ticket_count == empty.total_spent == 0 and not empty.favorite_numbers
        )

    def ticket(number: int, numbers: list[int], timestamp: datetime) -> dict:
        return dict(
            id=uuid4(),
            user_id=uid,
            lottery_id=lid,
            draw_id=did,
            public_number=number,
            numbers=numbers,
            purchase_price=100,
            purchased_at=timestamp,
        )

    old = [ticket(n, [1, 2, 3, 4, 5], now - timedelta(days=2)) for n in range(1, 1201)]
    recent = [
        ticket(n, [8, 9, 10, 11, 12], now + timedelta(seconds=n))
        for n in range(1201, 2202)
    ]
    async with session_factory() as session, session.begin():
        await session.execute(insert(Ticket), old + recent)
        session.add(
            InstantTicket(
                user_id=uid,
                symbols=[1, 1, 1],
                purchase_price=10,
                prize_amount=70,
                odds_version="profile-smoke",
            )
        )
        await session.flush()
        profile = await MiniAppQueryService(session).account(uid)
        assert profile.ticket_count == 2202 and profile.active_ticket_count == 2201
        assert (
            profile.total_spent == 220110
            and profile.total_won == profile.best_win == 70
        )
        assert profile.favorite_numbers == (
            8,
            9,
            10,
            11,
            12,
        )  # Ancient majority cannot win.
    await consistent()
    # Same inserted identifier is never counted twice when the write is replayed.
    replay = ticket(2202, [8, 9, 10, 11, 12], now + timedelta(hours=1))
    async with session_factory() as session, session.begin():
        for _ in range(2):
            await session.execute(
                pg_insert(Ticket)
                .values(**replay)
                .on_conflict_do_nothing(index_elements=[Ticket.id])
            )
    # Settlement and an approved-style refund change the display projection only
    # along with their source rows. This fixture contains no real money accounts.
    async with session_factory() as session, session.begin():
        await session.execute(
            update(Ticket)
            .where(Ticket.id == old[0]["id"])
            .values(status=TicketStatus.SETTLED, prize_amount=1234, settled_at=now)
        )
        await session.execute(
            update(Ticket)
            .where(Ticket.id == recent[-1]["id"])
            .values(status=TicketStatus.REFUNDED, settled_at=now)
        )
        profile = await MiniAppQueryService(session).account(uid)
        assert profile.active_ticket_count == 2200 and profile.winning_ticket_count == 2
        assert (
            profile.total_spent == 220110
            and profile.total_won == 1304
            and profile.best_win == 1234
        )
        assert profile.favorite_numbers == (8, 9, 10, 11, 12)
    await consistent()
    async with session_factory() as session:
        await session.execute(insert(Ticket), [ticket(2203, [1, 2, 3, 4, 5], now)])
        await session.rollback()
    await consistent()

    # Two independent writers must add to the same totals without a lost update.
    async def purchase(number: int) -> None:
        async with session_factory() as session, session.begin():
            await session.execute(
                insert(Ticket), [ticket(number, [8, 9, 10, 11, 12], now)]
            )

    await asyncio.gather(purchase(2203), purchase(2204))
    await consistent()
    notification_id = uuid4()
    async with session_factory() as session, session.begin():
        session.add(
            UserNotification(
                id=notification_id,
                user_id=uid,
                event_key="profile-smoke:unread",
                type=InAppNotificationType.WIN,
                title="Smoke",
                body="Smoke",
                payload={},
            )
        )
        session.add(
            UserNotification(
                user_id=uid,
                event_key="profile-smoke:result",
                type=InAppNotificationType.DRAW_RESULT,
                title="Smoke",
                body="Smoke",
                payload={},
            )
        )
        await session.flush()
        assert (
            await MiniAppQueryService(session).account(uid)
        ).unread_notification_count == 1
        await session.execute(
            update(UserNotification)
            .where(UserNotification.id == notification_id)
            .values(read_at=now)
        )
        assert (
            await MiniAppQueryService(session).account(uid)
        ).unread_notification_count == 0
    await consistent()
    # Rebuild repairs derived data and leaves source history byte-for-byte intact.
    async with session_factory() as session, session.begin():
        before = await session.scalar(
            text(
                "SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM tickets t"
            )
        )
        await session.execute(
            update(PlayerProfileStats)
            .where(PlayerProfileStats.user_id == uid)
            .values(total_spent=0)
        )
    async with session_factory() as session, session.begin():
        assert (await ProfileProjectionService(session).verify()).profiles == 1
        await ProfileProjectionService(session).rebuild()
        assert (
            await session.scalar(
                text(
                    "SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM tickets t"
                )
            )
            == before
        )
    await consistent()
    # The recent-window index must support the exact bounded favorites query.
    async with session_factory() as session:
        await session.execute(text("SET LOCAL enable_seqscan=off"))
        plan = await session.scalars(
            text(
                "EXPLAIN SELECT numbers FROM tickets WHERE user_id=:uid AND lottery_id=:lid AND status<>'REFUNDED' ORDER BY purchased_at DESC,id DESC LIMIT 1000"
            ),
            dict(uid=uid, lid=lid),
        )
        assert "ix_ticket_profile_recent" in "\n".join(plan)
    print(
        "Profile PostgreSQL: initial/instant/batch/replay/settlement/refund/rollback/concurrent/unread/rebuild/recent-1000/index PASS"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
