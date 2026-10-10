"""Distribution resets, durable result copy, and editorial expiry regressions."""

from collections import Counter
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from k_loto.application.distribution import queue_result, result_text
from k_loto.application.jackpot_cycles import cycle_ended
from k_loto.application.publication_automation import PublicationAutomation
from k_loto.application.publication_retention import proposal_expired, streak_epoch
from k_loto.application.publications import PublicationConflict
from k_loto.infrastructure.database.models import Draw, Lottery
from test_publications import Session, service, stored

NOW = datetime(2026, 10, 11, 8, tzinfo=UTC)


@pytest.mark.parametrize(
    "distributed,win,expected",
    [(101, False, True), (0, False, False), (0, True, True), (None, False, False)],
)
def test_jackpot_cycle_only_ends_when_paid(distributed, win, expected):
    draw = Draw(id=uuid4(), is_distribution=True, distributed_amount=distributed)
    assert cycle_ended(draw, {draw.id} if win else set()) is expected


def result_fixture():
    return Lottery(name="Casper Grand", code="weekly"), Draw(
        id=uuid4(),
        public_number=50,
        scheduled_at=NOW,
        ticket_count=4,
        total_payout=101_000,
        jackpot_closing=150_000_000,
    )


def test_result_counts_tickets_and_exact_integer_payouts():
    lottery, draw = result_fixture()
    text = result_text(lottery, draw, Counter({50_000: 2, 1_000: 1, 0: 1}), 100_001)
    assert "Из джекпота выплачено: 100 001 CAS" in text
    assert "Выигрышных билетов: 3." in text
    assert "Всего выигрышей: 101 000 CAS" in text
    assert "• 2 шт. — по 50 000 CAS" in text
    assert "11.10.2026 · 11:00 МСК" in text
    assert "150 000 000 CAS" in text
    assert "#Результаты" in text


def test_result_group_limit_keeps_complete_count_and_sum():
    lottery, draw = result_fixture()
    prizes = Counter({i: 2 for i in range(1, 101)})
    text = result_text(lottery, draw, prizes, 10_100)
    assert "Выигрышных билетов: 200." in text
    assert "Остальные 160 выигрышных билетов — всего 6 480 CAS" in text
    assert len(text) < 4096


def test_empty_distribution_reports_carry_forward():
    lottery, draw = result_fixture()
    draw.ticket_count, draw.total_payout = 0, 0
    text = result_text(lottery, draw, Counter(), 0)
    assert "Билетов не было — джекпот переносится" in text
    assert "Из джекпота выплачено: 0 CAS" in text


def test_result_is_queued_as_separate_receipt_in_callers_transaction():
    lottery, draw = result_fixture()
    session = Session()
    queue_result(session, lottery, draw, Counter({101_000: 1}), 100_000, NOW)
    row = session.added[0]
    assert row.draw_id == draw.id and row.kind == "result"
    assert row.state == "queued" and row.created_at == NOW


@pytest.mark.parametrize("hours,expired", [(23, False), (24, True), (25, True)])
def test_proposals_expire_at_exact_boundary_even_after_edit(hours, expired):
    row = stored()
    row.created_at = NOW - timedelta(hours=hours)
    row.updated_at = NOW
    assert proposal_expired(row, NOW) is expired


def test_importing_an_old_event_cannot_refresh_its_age():
    row = stored()
    row.created_at = NOW
    row.event_type = "A5.6"
    row.content = {
        **row.content,
        "delivery": {"state": "approval_required"},
        "event": {"occurred_at": (NOW - timedelta(days=2)).isoformat()},
    }
    assert proposal_expired(row, NOW)


@pytest.mark.parametrize(
    "status,state",
    [
        ("published", "approval_required"),
        ("archived", "approval_required"),
        ("draft", "queued"),
        ("draft", "sending"),
        ("draft", "uncertain"),
    ],
)
def test_expiry_preserves_history_and_authorized_delivery(status, state):
    row = stored(status)
    row.created_at = NOW - timedelta(days=2)
    row.event_type = "A5.6"
    row.content = {**row.content, "delivery": {"state": state}}
    assert not proposal_expired(row, NOW)


async def test_expired_proposal_cannot_be_published_or_edited():
    row = stored()
    row.created_at = datetime.now(UTC) - timedelta(days=2)
    for action in ("publish", "edit"):
        with pytest.raises(PublicationConflict, match="expired"):
            await service(Session(row)).change(
                row.id, author=row.author_id, revision=1, action=action
            )
    assert row.status == "draft" and row.revision == 1


def test_epoch_understands_legacy_and_current_proposals():
    row = stored()
    row.event_type, row.event_key = "A1.5", "A1.5:pulse:old-id:500"
    assert streak_epoch(row) == "old-id"
    row.content = {**row.content, "event": {"payload": {"reset_draw_id": "new-id"}}}
    assert streak_epoch(row) == "new-id"


async def test_statistics_starts_new_series_after_distribution():
    lottery = SimpleNamespace(id=uuid4(), code="weekly")
    draws = [
        Draw(
            id=uuid4(),
            lottery_id=lottery.id,
            executed_at=NOW - timedelta(hours=3 - i),
            scheduled_at=NOW - timedelta(hours=3 - i),
            distributed_amount=101 if i == 1 else 0,
            configuration_snapshot={},
            jackpot_opening=100,
            jackpot_closing=10,
            ticket_count=1,
        )
        for i in range(3)
    ]
    automation = PublicationAutomation(SimpleNamespace())
    automation.store = AsyncMock()
    await automation._statistics_a(
        NOW.replace(day=12, hour=0),
        NOW.replace(day=12, hour=12),
        uuid4(),
        {lottery.id: lottery},
        {"weekly": "Grand"},
        draws,
        {},
        {},
        {},
        False,
    )
    calls = [call for call in automation.store.call_args_list if call.args[0] == "A5.6"]
    assert len(calls) == 1
    assert calls[0].kwargs["payload"]["value"] == 1
    assert calls[0].kwargs["payload"]["reset_draw_id"] == str(draws[1].id)
