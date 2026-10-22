"""Private owner digest boundaries, financial meaning and durable delivery guards."""

from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.economy_reporting import EconomyDay, EconomyReportService
from k_loto.application.owner_economy import (
    OwnerEconomySummaryService,
    digest_metrics,
    due_report_day,
)
from k_loto.domain.enums import NotificationStatus, NotificationType
from k_loto.infrastructure.notification_repository import SqlNotificationRepository
from k_loto.infrastructure.telegram_messages import format_system_alert
from test_weekly_application import TransactionContext

NOW = datetime(2026, 10, 19, 21, 5, tzinfo=UTC)  # 20 October, 00:05 Moscow


def report():
    day = EconomyDay(
        day=date(2026, 10, 19),
        credited=160_000,
        debited=100_000,
        prizes=60_000,
        purchases=100_000,
        issued=100_000,
        burned=60_000,
        fund_debited=80_000,
    ).payload()
    return {"epoch": 2, "selected_day": date(2026, 10, 19), "days": [day]}


def test_moscow_day_is_complete_and_currency_growth_is_not_a_false_emergency():
    assert due_report_day(datetime(2026, 10, 19, 21, 4, 59, tzinfo=UTC)) is None
    assert due_report_day(NOW) == date(2026, 10, 19)
    assert due_report_day(datetime(2026, 10, 20, 10, tzinfo=UTC)) == date(2026, 10, 19)
    result = digest_metrics(report(), regular=15, instant=5, fund=8_000_000, pending=0)
    assert result["total_tickets"] == 20 and result["game_net"] == 40_000
    assert result["supply_net"] == 40_000 and result["attention"] is None
    assert result["fund_runway_days"] == 100
    message = format_system_alert(result)
    assert "Валюты стало больше: +40 000 CAS" in message
    assert "Сожжено: 60 000 CAS" in message and "не прибыль" in message
    assert "100 дн." in message and "не гарантия" in message
    assert "В джекпотах: 0 CAS" in message and len(message) < 4096


def test_runway_excludes_partial_epoch_days_and_does_not_claim_solvency():
    source = report()
    source["days"].insert(
        0, {**source["days"][0], "partial": True, "fund_net": -(10**12)}
    )
    result = digest_metrics(source, regular=0, instant=0, fund=1, pending=0)
    assert result["trend_days"] == 1 and result["fund_runway_days"] == 0
    assert result["attention"] == "fund_less_than_day"
    source["days"] = source["days"][:1]
    result = digest_metrics(source, regular=0, instant=0, fund=100, pending=2)
    assert (
        result["fund_runway_days"] is None and result["attention"] == "unresolved_draws"
    )
    source["days"][0]["partial"] = False
    source["days"][0]["fund_net"] = 100
    assert (
        digest_metrics(source, regular=0, instant=0, fund=0, pending=0)["attention"]
        == "fund_empty"
    )


class SummarySession:
    def __init__(self, values):
        self.scalar = AsyncMock(side_effect=values)
        self.execute = AsyncMock()
        self.info = {}

    def begin(self):
        return TransactionContext()


@pytest.mark.parametrize(
    "mode", ["queue", "existing", "paused", "old_day", "missing_owner"]
)
async def test_prepare_queues_once_only_for_the_current_epoch_and_owner(
    monkeypatch, mode
):
    control = SimpleNamespace(
        epoch=2,
        paused=mode == "paused",
        epoch_started_at=NOW
        if mode == "old_day"
        else datetime(2026, 10, 18, tzinfo=UTC),
    )
    user_id = uuid4()
    values = [
        control,
        SimpleNamespace(status=NotificationStatus.SENT) if mode == "existing" else None,
        None if mode == "missing_owner" else user_id,
        3,
        0,
        8_000_000,
        500_000,
        30_000,
        uuid4(),
    ]
    session = SummarySession(values)
    activity = MagicMock()
    activity.mappings.return_value.one.return_value = {
        "regular": 12,
        "fast": 3,
        "instant": 5,
        "gift": 7,
        "refunded": 1,
        "buyers": 2,
    }
    session.execute = AsyncMock(return_value=activity)
    daily = AsyncMock(return_value=report())
    monkeypatch.setattr(EconomyReportService, "daily", daily)
    result = await OwnerEconomySummaryService(cast(AsyncSession, session)).prepare(
        owner_telegram_id=123, now=NOW
    )
    assert result is (mode == "queue")
    if mode != "queue":
        daily.assert_not_awaited()
        return
    parameters = session.scalar.call_args.args[0].compile().params
    assert parameters["user_id"] == user_id
    assert parameters["event_key"] == "owner-economy:2:2026-10-19:123"
    assert parameters["payload"]["total_tickets"] == 20
    assert parameters["payload"]["new_players"] == 3
    assert parameters["payload"]["fast_tickets"] == 3
    assert parameters["payload"]["gift_tickets"] == 7
    assert "ON CONFLICT" in str(session.scalar.call_args.args[0])
    daily.assert_awaited_once_with(through=date(2026, 10, 19), now=NOW)


@pytest.mark.parametrize("mode", ["valid", "recipient", "epoch", "expired"])
async def test_claim_keeps_reports_private_and_cancels_old_reports(mode):
    payload = digest_metrics(report(), regular=1, instant=0, fund=100, pending=0)
    if mode == "epoch":
        payload["economy_epoch"] = 1
    if mode == "expired":
        payload["report_day"] = "2026-10-18"
    event = SimpleNamespace(
        id=uuid4(),
        event_key="report",
        type=NotificationType.SYSTEM_ALERT,
        payload=payload,
        status=NotificationStatus.PENDING,
        attempts=0,
    )
    user = SimpleNamespace(is_active=True, telegram_id=123)
    row = SimpleNamespace(one_or_none=lambda: (event, user, None))
    session = SummarySession([SimpleNamespace(epoch=2)])
    session.execute = AsyncMock(return_value=row)

    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *_):
            return None

    repository = SqlNotificationRepository(
        lambda: SessionContext(), owner_telegram_id=456 if mode == "recipient" else 123
    )
    claim = await repository.claim_next(NOW)
    assert claim is not None
    assert (claim.cancellation_reason is None) is (mode == "valid")


async def test_runtime_reconciles_on_startup_and_installs_the_report_job():
    from k_loto.infrastructure.scheduler import SchedulerRuntime

    runtime = SchedulerRuntime.__new__(SchedulerRuntime)
    runtime._scheduler = SimpleNamespace(add_job=Mock(), start=Mock())
    runtime._interval_seconds = 30
    runtime._run = AsyncMock()
    runtime._run_publication_events = AsyncMock()
    runtime._run_owner_economy = AsyncMock()
    await runtime.start()
    runtime._run_owner_economy.assert_awaited_once()
    jobs = runtime._scheduler.add_job.call_args_list
    job = next(x for x in jobs if x.kwargs["id"] == "owner-daily-economy")
    assert job.kwargs["seconds"] == 300 and job.kwargs["max_instances"] == 1


@pytest.mark.parametrize(
    "status,error,sent,recipient,expected",
    [
        (
            NotificationStatus.CANCELLED,
            "owner_report_recipient_changed",
            False,
            True,
            True,
        ),
        (NotificationStatus.CANCELLED, "owner_report_expired", False, True, False),
        (
            NotificationStatus.CANCELLED,
            "owner_report_recipient_changed",
            True,
            True,
            False,
        ),
        (
            NotificationStatus.UNCERTAIN,
            "owner_report_recipient_changed",
            False,
            True,
            False,
        ),
        (NotificationStatus.SENT, None, True, True, False),
        (
            NotificationStatus.CANCELLED,
            "owner_report_recipient_changed",
            False,
            False,
            False,
        ),
    ],
)
async def test_only_unsent_current_owner_configuration_failures_are_recovered(
    status, error, sent, recipient, expected
):
    owner = uuid4()
    event = SimpleNamespace(
        user_id=owner,
        status=status,
        last_error=error,
        sent_at=NOW if sent else None,
        locked_at=NOW,
        available_at=NOW,
    )
    control = SimpleNamespace(epoch=2, paused=False, epoch_started_at=None)
    session = SummarySession([control, event, owner if recipient else uuid4()])
    result = await OwnerEconomySummaryService(cast(AsyncSession, session)).prepare(
        owner_telegram_id=123, now=NOW
    )
    assert result is expected
    if expected:
        assert event.status == NotificationStatus.PENDING
        assert event.last_error is None and event.locked_at is None
        assert "FOR UPDATE" in str(session.scalar.call_args_list[1].args[0])
    else:
        assert event.status == status


def test_production_api_and_delivery_bot_share_the_owner_setting():
    from pathlib import Path

    compose = (
        Path(__file__).resolve().parents[2] / "docker-compose.prod.yml"
    ).read_text()
    api = compose.split("  api:\n", 1)[1].split("  bot:\n", 1)[0]
    bot = compose.split("  bot:\n", 1)[1].split("  gateway:\n", 1)[0]
    setting = "      OWNER_TELEGRAM_ID: ${OWNER_TELEGRAM_ID:-1201541335}"
    assert setting in api and setting in bot


def test_readable_breakdown_and_multiple_warnings_never_hide_each_other():
    source = report()
    source["days"][0]["achievement_rewards"] = 20_000
    result = digest_metrics(
        source,
        regular=3,
        fast=5,
        instant=2,
        gifts=9,
        refunded_tickets=1,
        buyers=4,
        new_players=7,
        fund=0,
        pending=2,
    )
    assert result["total_tickets"] == 10
    assert result["other_credit"] == 80_000
    message = format_system_alert(result)
    for line in (
        "Куплено платных билетов: 10",
        "FAST: 5",
        "Мгновенные: 2",
        "Тиражные: 3",
        "Подарочных выдано отдельно: 9",
        "Новых игроков: 7",
        "Покупали билеты: 4",
        "Награды за достижения: 20 000 CAS",
        "Бонусы и прочие начисления: 80 000 CAS",
        "Не завершено тиражей",
        "Фонд Каспера пуст",
    ):
        assert line in message
    assert "Покупки − выигрыши" not in message
    assert len(message) < 4096


def test_long_fund_horizon_is_readable_and_old_queued_payloads_remain_supported():
    result = digest_metrics(report(), regular=3, instant=1, fund=10**15, pending=0)
    assert "больше 10 лет" in format_system_alert(result)
    # A queued pre-patch report cannot invent a historical FAST breakdown.
    for key in (
        "fast_tickets",
        "new_players",
        "gift_tickets",
        "achievement_rewards",
        "player_balances",
        "fund_daily_expense",
    ):
        result.pop(key)
    message = format_system_alert(result)
    assert "Тиражные и FAST: 3" in message
    assert "Новых игроков:" not in message
    assert len(message) < 4096
