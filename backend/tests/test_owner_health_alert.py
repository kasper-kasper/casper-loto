"""Backup supervision and owner alerts without live Telegram requests."""

import json
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from scripts import owner_health_alert as alerts
from scripts import server_health_monitor as monitor


def test_incident_and_recovery_are_each_sent_once(tmp_path, monkeypatch):
    send = Mock()
    monkeypatch.setattr(alerts, "send_message", send)
    path = tmp_path / "state.json"
    config = ("private-token", "123")
    assert alerts.deliver([], path, config, now=1) == "idle"
    for now in (2, 3):
        assert (
            alerts.deliver(["backup_missing_or_stale"], path, config, now=now) == "sent"
        )
    for now in (4, 5):
        assert alerts.deliver([], path, config, now=now) == "sent"
    assert send.call_count == 2
    assert "private-token" not in path.read_text()
    assert json.loads(path.read_text())["active"] is False


@pytest.mark.parametrize("recovery", [False, True])
def test_definitive_rejection_retries_after_delay(tmp_path, monkeypatch, recovery):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"active": recovery, "delivery": "sent"}))
    send = Mock(side_effect=[alerts.RetryDelivery(600), None])
    monkeypatch.setattr(alerts, "send_message", send)
    warnings = [] if recovery else ["backup_job_failed"]
    assert alerts.deliver(warnings, path, ("x", "1"), now=1) == "retry"
    assert alerts.deliver(warnings, path, ("x", "1"), now=600) == "retry"
    assert send.call_count == 1
    assert alerts.deliver(warnings, path, ("x", "1"), now=601) == "sent"
    assert send.call_count == 2


def test_ambiguous_delivery_is_not_replayed_and_claim_precedes_http(
    tmp_path, monkeypatch
):
    path = tmp_path / "state.json"

    def send(*_):
        assert json.loads(path.read_text())["delivery"] == "uncertain"
        raise TimeoutError("private-token")

    transport = Mock(side_effect=send)
    monkeypatch.setattr(alerts, "send_message", transport)
    for now in (1, 1000):
        assert (
            alerts.deliver(["backup_job_failed"], path, ("x", "1"), now=now)
            == "uncertain"
        )
    assert transport.call_count == 1
    assert "private-token" not in path.read_text()


@pytest.mark.parametrize(
    ("size", "age", "expected"),
    [
        (100, 100, []),
        (0, 100, ["backup_missing_or_stale"]),
        (100, 27 * 3600, ["backup_missing_or_stale"]),
        (100, -600, ["backup_missing_or_stale"]),
    ],
)
def test_backup_freshness(monkeypatch, size, age, expected):
    now = 1_800_000_000
    monkeypatch.setattr(
        monitor,
        "database_backup_candidates",
        lambda _: [SimpleNamespace(size=size, mtime_ns=int((now - age) * 1e9))],
    )
    monkeypatch.setattr(
        monitor.subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], 0, "success\n")),
    )
    assert monitor.inspect_backups(now) == expected


def test_failed_backup_job_is_visible_even_with_fresh_copy(monkeypatch):
    monkeypatch.setattr(
        monitor,
        "database_backup_candidates",
        lambda _: [SimpleNamespace(size=100, mtime_ns=1_800_000_000 * 1e9)],
    )
    monkeypatch.setattr(
        monitor.subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], 0, "exit-code\n")),
    )
    assert monitor.inspect_backups(1_800_000_000) == ["backup_job_failed"]


def test_unverified_volume_fails_closed(monkeypatch):
    monkeypatch.setattr(
        monitor, "database_backup_candidates", Mock(side_effect=RuntimeError)
    )
    monkeypatch.setattr(
        monitor.subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], 0, "success\n")),
    )
    assert monitor.inspect_backups(1_800_000_000) == ["backup_check_failed"]
