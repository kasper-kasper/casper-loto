"""Transactional event smoke, strictly restricted to a disposable *_smoke database."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

from k_loto.application.publication_events import (
    EventDraftInput,
    MilestoneRule,
    PublicationEventService,
    event_config,
)
from k_loto.application.publications import PublicationConflict, PublicationService
from k_loto.core.config import get_settings
from k_loto.domain.enums import DrawStatus
from k_loto.infrastructure.database.models import (
    Draw,
    InstantTicket,
    JackpotWinEvent,
    Lottery,
    Publication,
    User,
)
from k_loto.infrastructure.database.session import engine, session_factory


async def main() -> None:
    if not str(get_settings().database_url).rsplit("/", 1)[-1].endswith("_smoke"):
        raise RuntimeError("Event smoke requires a disposable *_smoke database.")
    now = datetime.now(UTC)
    async with session_factory() as session, session.begin():
        author = await session.scalar(
            select(User.id).where(User.is_admin.is_(True)).limit(1)
        )
        lottery = await session.scalar(select(Lottery).where(Lottery.code == "weekly"))
        assert author is not None and lottery is not None
        next_number = (
            int(
                await session.scalar(
                    select(func.max(Draw.public_number)).where(
                        Draw.lottery_id == lottery.id
                    )
                )
                or 0
            )
            + 1
        )
        for offset in range(4):
            draw_id = uuid4()
            session.add(
                Draw(
                    id=draw_id,
                    lottery_id=lottery.id,
                    public_number=next_number + offset,
                    status=DrawStatus.COMPLETED,
                    scheduled_at=now - timedelta(minutes=5),
                    sales_close_at=now - timedelta(minutes=10),
                    executed_at=now - timedelta(minutes=4),
                    winning_numbers=[1],
                    correlation_id=uuid4(),
                    configuration_snapshot={},
                )
            )
            await session.flush()
            session.add(
                JackpotWinEvent(
                    id=uuid4(),
                    draw_id=draw_id,
                    lottery_id=lottery.id,
                    jackpot_amount=1,
                    winner_ticket_count=1,
                    winner_user_count=1,
                    base_jackpot_after=1,
                    occurred_at=now - timedelta(minutes=4),
                )
            )
        session.add(
            InstantTicket(
                id=uuid4(),
                user_id=author,
                symbols=[1, 1, 1],
                purchase_price=1,
                prize_amount=1,
                odds_version="event-smoke",
                purchased_at=now - timedelta(minutes=1),
                settled_at=now - timedelta(minutes=1),
            )
        )
    config = event_config()
    async with session_factory() as session:
        counters = await PublicationEventService(session).metrics()
    for code, rule in list(config.milestones.items()):
        config.milestones[code] = MilestoneRule(
            metric=rule.metric, thresholds=[max(1, counters[rule.metric])]
        )

    async def scan() -> None:
        async with session_factory() as session:
            await PublicationEventService(session, config).scan(
                now=now, force=True, author=author
            )

    await asyncio.gather(*(scan() for _ in range(4)))
    async with session_factory() as session:
        rows = list(
            await session.scalars(
                select(Publication).where(Publication.event_type.is_not(None))
            )
        )
        assert len({r.event_key for r in rows}) == len(rows)
        for code, rule in config.milestones.items():
            assert (
                len(
                    [
                        r
                        for r in rows
                        if r.event_type == code
                        and r.content["event"]["payload"]["threshold"]
                        == rule.thresholds[0]
                    ]
                )
                == 1
            )
        assert any(r.event_type == "B3.5" for r in rows)
        assert all(r.status == "draft" and "template" not in r.content for r in rows)
        assert all(
            row.event_type is None
            for row in await PublicationService(session).list(player=True)
        )
    draft_id = uuid4()

    async def draft() -> None:
        async with session_factory() as session:
            row = await PublicationEventService(session).create_draft(
                EventDraftInput(event_type="B4.8", fields={"version": "smoke"}),
                publication_id=draft_id,
                author=author,
                now=now,
            )
            assert row.id == draft_id and row.event_mode == "draft"

    await asyncio.gather(draft(), draft())
    async with session_factory() as session:
        try:
            await PublicationService(session).change(
                draft_id, author=author, revision=1, action="publish"
            )
        except PublicationConflict:
            pass
        else:
            raise AssertionError("Nonvisual draft must never publish.")
    for code in ("B3.1", "B3.2", "B3.3", "B3.4"):
        request = (
            EventDraftInput(
                event_type=code, period_start=now - timedelta(days=7), period_end=now
            )
            if code in ("B3.3", "B3.4")
            else EventDraftInput(event_type=code)
        )
        async with session_factory() as session:
            row = await PublicationEventService(session).create_draft(
                request, publication_id=uuid4(), author=author, now=now
            )
            assert row.status == "draft"
    await engine.dispose()
    print(
        "PostgreSQL event smoke: concurrent scan/draft dedupe, Moscow aggregates, "
        "instant metrics, B3 drafts and publish guard passed."
    )


if __name__ == "__main__":
    asyncio.run(main())
