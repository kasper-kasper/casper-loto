"""Read-only delivery health using the dispatcher's head and pacing policy."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.publication_events import DeliveryPolicy, event_config
from k_loto.infrastructure.database.models import Publication, PublicationEventState


def queued_delivery_due_at(
    delivery: dict[str, Any],
    *,
    fallback: datetime,
    last_sent_at: str | None,
    policy: DeliveryPolicy,
) -> datetime:
    """Never move an overdue deadline forward merely because time has passed."""
    queued_at = (
        datetime.fromisoformat(delivery["queued_at"]).astimezone(UTC)
        if delivery.get("queued_at")
        else fallback
    )
    bypass = bool(delivery.get("manual") or delivery.get("historical"))
    last_sent = (
        datetime.fromisoformat(last_sent_at).astimezone(UTC)
        if last_sent_at and not bypass
        else None
    )
    due = policy.earliest(
        queued_at,
        last_sent,
        manual=bypass,
    )
    if delivery.get("retry_after"):
        due = max(due, datetime.fromisoformat(delivery["retry_after"]).astimezone(UTC))
    return due


async def delayed_publications(
    session: AsyncSession, *, now: datetime, grace: timedelta
) -> int:
    from k_loto.application.publication_automation import publication_eligibility_filter
    from k_loto.application.publication_retention import stale_streak_filter
    from k_loto.core.config import get_settings

    if not get_settings().editorial_enabled:
        return 0
    cutoff = now - grace
    delivery = Publication.content["delivery"]
    active = Publication.status == "draft"
    # Failure/uncertainty remains actionable even when transport is paused.
    problems = int(
        await session.scalar(
            select(func.count(Publication.id)).where(
                active,
                delivery["state"].astext.in_(["failed", "uncertain", "sending"]),
                Publication.updated_at < cutoff,
            )
        )
        or 0
    )
    transport = await session.get(PublicationEventState, "publication.transport")
    if transport is None or not transport.value.get("enabled"):
        return problems
    # The dispatcher cannot pass an unresolved send; report that blocker once.
    blocked = await session.scalar(
        select(Publication.id)
        .where(active, delivery["state"].astext.in_(["sending", "uncertain"]))
        .limit(1)
    )
    if blocked is not None:
        return problems
    head = await session.scalar(
        select(Publication)
        .where(
            active,
            delivery["state"].astext == "queued",
            publication_eligibility_filter(),
            ~stale_streak_filter(),
        )
        .order_by(Publication.content["event"]["occurred_at"].astext, Publication.id)
        .limit(1)
    )
    if head is None:
        return problems
    due = queued_delivery_due_at(
        head.content["delivery"],
        fallback=head.updated_at,
        last_sent_at=transport.value.get("last_automatic_sent_at"),
        policy=event_config().delivery,
    )
    return problems + int(due < cutoff)
