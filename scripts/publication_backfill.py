"""Owner-authorized one-off replay. Preparing never enables Telegram transport."""

import argparse
import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, literal_column, select, update

from k_loto.application.publication_automation import (
    PublicationAutomation,
    publication_eligibility_filter,
)
from k_loto.application.publication_events import PublicationEventService
from k_loto.infrastructure.database.models import Publication
from k_loto.infrastructure.database.session import engine, session_factory


async def run(action: str) -> None:
    if action in {"prepare", "restart"}:
        async with session_factory() as session, session.begin():
            service = PublicationEventService(session)
            await service._lock()
            job = await service._state("publication.backfill.2026-09-25")
            if not job.value:
                job.value = {
                    "start": datetime(2026, 9, 25, tzinfo=ZoneInfo("Europe/Moscow"))
                    .astimezone(UTC)
                    .isoformat(),
                    "end": datetime.now(UTC).isoformat(),
                    "include_calculated_drafts": True,
                }
            if action == "restart":
                transport = await service._state("publication.transport")
                if transport.value.get("enabled"):
                    raise ValueError("Stop delivery before restarting the replay")
                job.value = {
                    **job.value,
                    "end": datetime.now(UTC).isoformat(),
                    "prepared": False,
                    "owner_repeat_authorization": "2026-10-06",
                }
            bounds = dict(job.value)
        async with session_factory() as session:
            counts = await PublicationAutomation(session).collect(
                datetime.fromisoformat(bounds["start"]),
                datetime.fromisoformat(bounds["end"]),
                historical=True,
            )
        async with session_factory() as session, session.begin():
            service = PublicationEventService(session)
            await service._lock()
            # Keep excluded rows for audit, but never send them or expose as Stories.
            await session.execute(
                update(Publication)
                .where(
                    Publication.event_type.is_not(None),
                    ~publication_eligibility_filter(),
                )
                .values(
                    content=func.jsonb_set(
                        Publication.content,
                        literal_column("'{story_visible}'::text[]"),
                        literal_column("'false'::jsonb"),
                    )
                )
            )
            await session.execute(
                update(Publication)
                .where(
                    ~publication_eligibility_filter(),
                    Publication.content["delivery"]["state"].astext.in_(
                        ["queued", "approval_required"]
                    ),
                )
                .values(
                    content=func.jsonb_set(
                        Publication.content,
                        literal_column("'{delivery,state}'::text[]"),
                        literal_column("'\"excluded_by_rules\"'::jsonb"),
                    )
                )
            )
            if action == "restart":
                pending = await session.scalar(
                    select(Publication.id)
                    .where(
                        Publication.content["delivery"]["state"].astext.in_(
                            ["sending", "uncertain"]
                        )
                    )
                    .limit(1)
                )
                if pending:
                    raise ValueError("Resolve in-flight delivery before restarting")
                replayed = 0
                for row in await session.scalars(
                    select(Publication).where(
                        publication_eligibility_filter(),
                        Publication.content.has_key("template"),
                        Publication.content["event"]["occurred_at"].astext
                        >= bounds["start"],
                        Publication.content["event"]["occurred_at"].astext
                        <= bounds["end"],
                    )
                ):
                    content = deepcopy(row.content)
                    if content["delivery"].get("state") == "sent":
                        content.setdefault("delivery_history", []).append(
                            content["delivery"]
                        )
                    content["delivery"] = {
                        "state": "queued",
                        "historical": True,
                        "replay": bounds["end"],
                    }
                    content["story_visible"] = False
                    row.content = content
                    row.status = "draft"
                    row.published_at = None
                    row.revision += 1
                    replayed += 1
                await session.flush()
                counts = {"eligible_replay_posts": replayed}
            job = await service._state("publication.backfill.2026-09-25")
            job.value = {**job.value, "prepared": True, "counts": counts}
            candidates = list(
                await session.scalars(
                    select(Publication)
                    .where(
                        publication_eligibility_filter(),
                        Publication.content["delivery"]["historical"]
                        .as_boolean()
                        .is_(True),
                    )
                    .order_by(
                        Publication.content["event"]["occurred_at"].astext.desc(),
                        Publication.id.desc(),
                    )
                    .limit(10)
                )
            )
            for row in candidates:
                row.content = {**row.content, "story_visible": True}
        print(json.dumps({"prepared": counts, "window": bounds}, ensure_ascii=False))
    elif action == "enable":
        async with session_factory() as session, session.begin():
            service = PublicationEventService(session)
            await service._lock()
            job = await service._state("publication.backfill.2026-09-25")
            if not job.value.get("prepared"):
                raise ValueError("Prepare the durable historical job before enabling")
            state = await service._state("publication.transport")
            state.value = {
                **state.value,
                "enabled": True,
                "minimum_interval_seconds": 1800,
                "historical_interval_seconds": 0,
                "owner_authorization": "2026-10-06",
                "enabled_at": datetime.now(UTC).isoformat(),
            }
        print(
            "Telegram automatic transport enabled; "
            "historical posts have no editorial interval"
        )
    elif action == "status":
        async with session_factory() as session:
            delivery_state = Publication.content["delivery"]["state"].astext.label(
                "delivery_state"
            )
            status_counts = (
                await session.execute(
                    select(delivery_state, func.count())
                    .where(Publication.event_type.is_not(None))
                    .group_by("delivery_state")
                )
            ).all()
            print(
                json.dumps(
                    {str(key): int(count) for key, count in status_counts},
                    ensure_ascii=False,
                )
            )
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "restart", "enable", "status"])
    asyncio.run(run(parser.parse_args().action))
