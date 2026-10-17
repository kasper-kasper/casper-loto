"""Publication health distinguishes ordinary pacing from a stuck dispatcher."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.publication_events import DeliveryPolicy
from k_loto.application.publication_monitoring import (
    delayed_publications,
    queued_delivery_due_at,
)

NOW = datetime(2026, 10, 17, 9, 22, tzinfo=UTC)
POLICY = DeliveryPolicy(minimum_interval_seconds=1800)


@pytest.mark.parametrize(
    "delivery,last_sent,expected",
    [
        ({"queued_at": NOW.isoformat()}, None, NOW),
        ({"queued_at": NOW.isoformat()}, NOW.isoformat(), NOW + timedelta(minutes=30)),
        ({"manual": True}, NOW.isoformat(), NOW - timedelta(hours=4)),
        ({"historical": True}, NOW.isoformat(), NOW - timedelta(hours=4)),
        ({"manual": True}, "unused", NOW - timedelta(hours=4)),
        ({}, None, NOW - timedelta(hours=4)),
        (
            {"retry_after": (NOW + timedelta(hours=1)).isoformat()},
            NOW.isoformat(),
            NOW + timedelta(hours=1),
        ),
    ],
)
def test_due_uses_queue_entry_pacing_bypass_and_retry(delivery, last_sent, expected):
    assert (
        queued_delivery_due_at(
            delivery,
            fallback=NOW - timedelta(hours=4),
            last_sent_at=last_sent,
            policy=POLICY,
        )
        == expected
    )


@pytest.mark.parametrize(
    "minute,expected", [(1, 0), (30, 0), (40, 0), (41, 1), (90, 1)]
)
async def test_queue_head_becomes_late_only_after_its_slot_and_grace(minute, expected):
    session = AsyncMock(spec=AsyncSession)
    head = SimpleNamespace(
        updated_at=NOW - timedelta(hours=4),
        content={"delivery": {"queued_at": NOW.isoformat()}},
    )
    session.scalar.side_effect = [0, None, head]
    session.get.return_value = SimpleNamespace(
        value={"enabled": True, "last_automatic_sent_at": NOW.isoformat()}
    )
    assert (
        await delayed_publications(
            session, now=NOW + timedelta(minutes=minute), grace=timedelta(minutes=10)
        )
        == expected
    )


@pytest.mark.parametrize("enabled,blocked", [(False, None), (True, "blocked")])
async def test_disabled_or_blocked_transport_still_reports_real_failures(
    enabled, blocked
):
    session = AsyncMock(spec=AsyncSession)
    session.scalar.side_effect = [2, blocked]
    session.get.return_value = SimpleNamespace(value={"enabled": enabled})
    assert (
        await delayed_publications(session, now=NOW, grace=timedelta(minutes=10)) == 2
    )
    assert session.scalar.await_count == (2 if enabled else 1)
