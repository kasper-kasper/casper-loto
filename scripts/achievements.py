"""Manage achievement foundation only in a dedicated local database."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from k_loto.application.achievement_catalog import (
    CatalogEntry,
    import_catalog,
    launch_local,
    require_local,
)
from k_loto.application.achievements import drain
from k_loto.infrastructure.database.achievement_models import (
    AchievementEvent,
    AchievementRuntime,
)
from k_loto.infrastructure.database.session import engine, session_factory


async def run(args: argparse.Namespace) -> None:
    production = args.command.startswith("production-")
    if production:
        from k_loto.application.achievement_release import require_production

        require_production()
        if not args.confirm_production:
            raise ValueError("Explicit --confirm-production is required")
    else:
        async with session_factory() as session:
            require_local(session)
    if args.command == "production-schedule":
        from k_loto.application.achievement_release import schedule_production

        async with session_factory() as session, session.begin():
            scheduled = await schedule_production(
                session, datetime.fromisoformat(args.at)
            )
        print(json.dumps({"scheduled_at": scheduled.isoformat(), "enabled": False}))
    elif args.command in {"production-cancel", "production-pause", "production-resume"}:
        from k_loto.application.achievement_release import (
            cancel_schedule,
            pause_processing,
        )

        async with session_factory() as session, session.begin():
            if args.command == "production-cancel":
                await cancel_schedule(session)
            else:
                await pause_processing(
                    session, paused=args.command == "production-pause"
                )
        print(json.dumps({"operation": args.command, "ok": True}))
    elif args.command in {
        "common-catalog",
        "uncommon-catalog",
        "rare-catalog",
        "epic-catalog",
        "legendary-catalog",
    }:
        from k_loto.application.common_achievements import common_catalog
        from k_loto.application.epic_achievements import epic_catalog
        from k_loto.application.legendary_achievements import legendary_catalog
        from k_loto.application.rare_achievements import rare_catalog
        from k_loto.application.uncommon_achievements import uncommon_catalog

        entries = {
            "common-catalog": common_catalog,
            "uncommon-catalog": uncommon_catalog,
            "rare-catalog": rare_catalog,
            "epic-catalog": epic_catalog,
            "legendary-catalog": legendary_catalog,
        }[args.command]()
        async with session_factory() as session, session.begin():
            await import_catalog(session, entries)
        print(
            json.dumps(
                {
                    "imported": len(entries),
                    "rewards": "approved_local",
                    "cases": "planned",
                }
            )
        )
    elif args.command == "catalog":
        entries = [
            CatalogEntry.model_validate(item)
            for item in json.loads(
                await asyncio.to_thread(Path(args.file).read_text, encoding="utf-8-sig")
            )
        ]
        async with session_factory() as session, session.begin():
            await import_catalog(session, entries)
        print(json.dumps({"imported": len(entries)}))
    elif args.command == "launch-local":
        async with session_factory() as session, session.begin():
            started = await launch_local(session)
        print(json.dumps({"started_at": started.isoformat()}))
    elif args.command == "drain":
        print(json.dumps({"batches": await drain(session_factory, limit=args.limit)}))
    elif args.command == "retry":
        async with session_factory() as session, session.begin():
            event = await session.get(
                AchievementEvent, args.event_id, with_for_update=True
            )
            if event is None or event.processed_at is not None:
                raise ValueError("An unfinished event is required")
            event.attempts, event.available_at = 0, datetime.now(UTC)
        print(json.dumps({"retried_event": args.event_id}))
    else:
        async with session_factory() as session:
            state = await session.get(AchievementRuntime, 1)
            pending = await session.scalar(
                select(func.count())
                .select_from(AchievementEvent)
                .where(AchievementEvent.processed_at.is_(None))
            )
            failed = await session.scalar(
                select(func.count())
                .select_from(AchievementEvent)
                .where(
                    AchievementEvent.processed_at.is_(None),
                    AchievementEvent.last_error.is_not(None),
                )
            )
            oldest = await session.scalar(
                select(func.min(AchievementEvent.occurred_at)).where(
                    AchievementEvent.processed_at.is_(None)
                )
            )
            print(
                json.dumps(
                    {
                        "enabled": bool(state and state.enabled),
                        "started_at": state.started_at.isoformat()
                        if state and state.started_at
                        else None,
                        "scheduled_at": state.scheduled_at.isoformat()
                        if state and state.scheduled_at
                        else None,
                        "processing_paused": bool(state and state.processing_paused),
                        "pending": pending,
                        "failed": failed,
                        "oldest": oldest.isoformat() if oldest else None,
                    }
                )
            )
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("launch-local")
    sub.add_parser("common-catalog")
    sub.add_parser("uncommon-catalog")
    sub.add_parser("rare-catalog")
    sub.add_parser("epic-catalog")
    sub.add_parser("legendary-catalog")
    for name in (
        "production-schedule",
        "production-cancel",
        "production-pause",
        "production-resume",
        "production-status",
    ):
        production = sub.add_parser(name)
        production.add_argument("--confirm-production", action="store_true")
        if name == "production-schedule":
            production.add_argument(
                "--at", required=True, help="ISO date/time with timezone"
            )
    catalog = sub.add_parser("catalog")
    catalog.add_argument("file")
    worker = sub.add_parser("drain")
    worker.add_argument("--limit", type=int, choices=range(1, 10001), default=100)
    retry = sub.add_parser("retry")
    retry.add_argument("event_id", type=int)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
