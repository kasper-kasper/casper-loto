"""Owner-authorized one-off replay. Preparing never enables Telegram transport."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from k_loto.application.publication_automation import PublicationAutomation
from k_loto.application.publication_events import PublicationEventService
from k_loto.infrastructure.database.models import Publication
from k_loto.infrastructure.database.session import engine, session_factory


async def run(action: str) -> None:
    if action == "prepare":
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
            bounds = dict(job.value)
        async with session_factory() as session:
            counts = await PublicationAutomation(session).collect(
                datetime.fromisoformat(bounds["start"]),
                datetime.fromisoformat(bounds["end"]),
                historical=True,
            )
        async with session_factory() as session, session.begin():
            job = await PublicationEventService(session)._state(
                "publication.backfill.2026-09-25"
            )
            job.value = {**job.value, "prepared": True, "counts": counts}
            candidates = list(
                await session.scalars(
                    select(Publication)
                    .where(
                        Publication.content["delivery"]["historical"]
                        .as_boolean()
                        .is_(True)
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
            counts = (
                await session.execute(
                    select(delivery_state, func.count())
                    .where(Publication.event_type.is_not(None))
                    .group_by("delivery_state")
                )
            ).all()
            print(json.dumps(dict(counts), ensure_ascii=False))
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "enable", "status"])
    asyncio.run(run(parser.parse_args().action))
