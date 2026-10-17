"""Real delivery-health queries in a fresh disposable schema, without Telegram I/O."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

from k_loto.application.publication_monitoring import delayed_publications
from k_loto.infrastructure.database.models import (
    Publication,
    PublicationEventState,
    User,
)
from k_loto.infrastructure.database.session import engine, session_factory


async def main() -> None:
    if not str(engine.url.database).startswith("k_loto_audit_stage1_"):
        raise RuntimeError("Fresh disposable audit database required")
    start = datetime(2026, 10, 17, 9, 22, tzinfo=UTC)
    grace = timedelta(minutes=10)
    async with session_factory() as session:
        assert await session.scalar(select(func.count(Publication.id))) == 0
        owner = User(id=uuid4(), display_name="Synthetic monitoring owner")
        session.add(owner)
        await session.flush()
        transport = await session.get(PublicationEventState, "publication.transport")
        if transport is None:
            transport = PublicationEventState(key="publication.transport", value={})
            session.add(transport)

        def pace(last: datetime | None, enabled: bool = True) -> None:
            transport.value = {
                "enabled": enabled,
                **({"last_automatic_sent_at": last.isoformat()} if last else {}),
            }

        def post(state="queued", status="draft", code="A1.1", **delivery):
            row = Publication(
                id=uuid4(),
                author_id=owner.id,
                lottery_code="weekly",
                status=status,
                event_type=code,
                revision=1,
                created_at=start - timedelta(hours=4),
                updated_at=start - timedelta(hours=4),
                content={
                    "event": {"occurred_at": (start - timedelta(hours=4)).isoformat()},
                    "delivery": {
                        "state": state,
                        "queued_at": start.isoformat(),
                        **delivery,
                    },
                },
            )
            session.add(row)
            return row

        async def check(minute: int, expected: int) -> None:
            await session.flush()
            actual = await delayed_publications(
                session, now=start + timedelta(minutes=minute), grace=grace
            )
            assert actual == expected, (minute, actual, expected)

        pace(start)
        first, second = post(), post()
        first.content = {
            **first.content,
            "event": {"occurred_at": (start - timedelta(hours=5)).isoformat()},
        }
        post(
            status="published"
        )  # Legacy delivery state cannot revive completed content.
        post(status="archived")
        post(state="approval_required")
        post(code="A2.1")  # Ineligible routine events never join the dispatcher head.
        stale = post(code="A1.5")
        stale.content["event"]["payload"] = {"reset_draw_id": str(uuid4())}
        await check(1, 0)
        await check(30, 0)
        await check(41, 1)  # First head really missed its permitted slot.
        first.status = "published"
        pace(start + timedelta(minutes=30))
        await check(31, 0)
        await check(60, 0)
        await check(71, 1)  # Second waits for the next slot, not source-event age.
        second.status = "archived"
        pace(None)
        head = post()
        await check(5, 0)
        await check(11, 1)  # No previous send: use actual queue-entry time.
        head.content = {
            **head.content,
            "delivery": {
                **head.content["delivery"],
                "retry_after": (start + timedelta(hours=1)).isoformat(),
            },
        }
        await check(59, 0)
        await check(71, 1)
        pace(start, enabled=False)
        await check(71, 0)
        for bypass in ("manual", "historical"):
            pace(start + timedelta(hours=2))
            head.content = {
                **head.content,
                "delivery": {
                    "state": "queued",
                    "queued_at": start.isoformat(),
                    bypass: True,
                },
            }
            await check(11, 1)
        head.status = "archived"
        bad = post(state="failed")
        await check(11, 1)
        pace(None, enabled=False)
        await check(11, 1)  # Pause does not silence delivery errors.
        bad.status = "archived"
        pace(None)
        post()  # A blocked queue is accounted for through the blocking send only.
        blocker = post(state="uncertain")
        await check(11, 1)
        blocker.content = {**blocker.content, "delivery": {"state": "sending"}}
        blocker.updated_at = start + timedelta(minutes=5)
        await check(11, 0)
        await check(16, 1)
        await session.rollback()
    await engine.dispose()
    print(
        "Publication monitoring: paced head, queue age, retry, bypass, "
        "disabled transport, failures and archived/ineligible rows PASS"
    )


if __name__ == "__main__":
    asyncio.run(main())
