"""Unanswered editorial proposals expire without deleting publication history."""

from copy import deepcopy
from datetime import datetime, timedelta

from sqlalchemy import DateTime, String, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from k_loto.domain.enums import DrawStatus
from k_loto.infrastructure.database.models import Draw, Lottery, Publication

PROPOSAL_LIFETIME = timedelta(hours=24)


def streak_epoch(row: Publication) -> str:
    recorded = row.content.get("event", {}).get("payload", {}).get("reset_draw_id")
    if recorded:
        return str(recorded)
    parts = (row.event_key or "").split(":")
    return parts[2] if row.event_type == "A1.5" and len(parts) >= 4 else "origin"


def stale_streak_filter() -> ColumnElement[bool]:
    from k_loto.application.jackpot_cycles import cycle_end_filter

    latest = (
        select(Draw.id)
        .join(Lottery, Lottery.id == Draw.lottery_id)
        .where(
            Lottery.code == Publication.lottery_code,
            Draw.status == DrawStatus.COMPLETED,
            cycle_end_filter(),
        )
        .order_by(Draw.scheduled_at.desc(), Draw.public_number.desc())
        .limit(1)
        .correlate(Publication)
        .scalar_subquery()
    )
    recorded = func.coalesce(
        Publication.content["event"]["payload"]["reset_draw_id"].astext,
        case(
            (
                Publication.event_type == "A1.5",
                func.nullif(func.split_part(Publication.event_key, ":", 3), ""),
            ),
            else_="origin",
        ),
        "origin",
    )
    return func.coalesce(
        and_(
            Publication.status == "draft",
            Publication.event_type.in_(["A1.5", "A5.6"]),
            Publication.content["delivery"]["state"].astext.in_(
                ["approval_required", "queued"]
            ),
            recorded != func.coalesce(cast(latest, String), "origin"),
        ),
        False,
    )


async def stale_streak(session: AsyncSession, row: Publication) -> bool:
    from k_loto.application.jackpot_cycles import cycle_end_filter

    if row.event_type not in {"A1.5", "A5.6"} or row.status != "draft":
        return False
    latest = await session.scalar(
        select(Draw.id)
        .join(Lottery, Lottery.id == Draw.lottery_id)
        .where(
            Lottery.code == row.lottery_code,
            Draw.status == DrawStatus.COMPLETED,
            cycle_end_filter(),
        )
        .order_by(Draw.scheduled_at.desc(), Draw.public_number.desc())
        .limit(1)
    )
    return streak_epoch(row) != (str(latest) if latest else "origin")


def pending_proposal_filter() -> ColumnElement[bool]:
    return and_(
        Publication.status == "draft",
        or_(
            Publication.event_type.is_(None),
            Publication.content["delivery"]["state"].astext == "approval_required",
        ),
    )


def proposal_timestamp() -> ColumnElement[datetime]:
    occurred = cast(
        Publication.content["event"]["occurred_at"].astext, DateTime(timezone=True)
    )
    return func.least(
        Publication.created_at, func.coalesce(occurred, Publication.created_at)
    )


def proposal_expired(row: Publication, now: datetime) -> bool:
    if row.status != "draft" or (
        row.event_type
        and row.content.get("delivery", {}).get("state") != "approval_required"
    ):
        return False
    occurred = row.content.get("event", {}).get("occurred_at")
    stamp = (
        min(row.created_at, datetime.fromisoformat(occurred))
        if occurred
        else row.created_at
    )
    return now >= stamp + PROPOSAL_LIFETIME


async def expire_proposals(
    factory: async_sessionmaker[AsyncSession], *, now: datetime
) -> int:
    from k_loto.application.publication_events import PublicationEventService
    from k_loto.application.publications import PublicationService

    async with factory() as session, session.begin():
        await PublicationEventService(session)._lock()
        rows = (
            await session.scalars(
                select(Publication)
                .where(
                    or_(
                        and_(
                            pending_proposal_filter(),
                            proposal_timestamp() <= now - PROPOSAL_LIFETIME,
                        ),
                        stale_streak_filter(),
                    ),
                )
                .order_by(Publication.created_at, Publication.id)
                .limit(500)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for row in rows:
            reason = "24_hours" if proposal_expired(row, now) else "jackpot_cycle_ended"
            old = {
                "status": row.status,
                "revision": row.revision,
                "content": deepcopy(row.content),
            }
            row.status, row.updated_at = "archived", now
            row.revision += 1
            row.content = {
                **deepcopy(row.content),
                "proposal_expiration": {"at": now.isoformat(), "reason": reason},
            }
            PublicationService(session)._audit(
                row, row.author_id, f"automatic_expire_{reason}", old
            )
        return len(rows)
