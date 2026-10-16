"""Independent watchdog exposes only health codes, never raw Docker diagnostics."""

import json
import subprocess
from unittest.mock import Mock

from scripts import server_health_monitor


def test_container_failures_become_redacted_codes(monkeypatch) -> None:
    run = Mock(
        side_effect=[
            subprocess.CompletedProcess(
                [], 0, '{"Running":true,"Health":{"Status":"healthy"}}'
            ),
            subprocess.CompletedProcess(
                [], 0, '{"Running":true,"Health":{"Status":"unhealthy"}}'
            ),
            subprocess.CompletedProcess([], 0, '{"Running":false}'),
            subprocess.CalledProcessError(1, "docker", stderr="private diagnostic"),
        ]
    )
    monkeypatch.setattr(server_health_monitor.subprocess, "run", run)
    result = server_health_monitor.inspect_services()
    assert len(result) == 3
    assert all("private" not in item for item in result)
    assert "service_unhealthy:k-loto-api-1" in result


def test_host_report_is_one_atomic_redacted_file(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(server_health_monitor, "ROOT", tmp_path)
    monkeypatch.setattr(server_health_monitor, "inspect_services", lambda: [])
    monkeypatch.setattr(server_health_monitor, "inspect_backups", lambda _: [])
    monkeypatch.setattr(server_health_monitor, "notify", lambda *_: "idle")
    response = Mock()
    response.status = 200
    response.read.return_value = b'{"status":"ok"}'
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(server_health_monitor, "urlopen", Mock(return_value=response))
    run = Mock(
        return_value=subprocess.CompletedProcess(
            [], 0, '{"event":"operational_snapshot"}\nprivate diagnostic'
        )
    )
    monkeypatch.setattr(server_health_monitor.subprocess, "run", run)
    server_health_monitor.main()
    server_health_monitor.main()
    files = list((tmp_path / ".monitoring").iterdir())
    assert [item.name for item in files] == ["state.json"]
    assert json.loads(files[0].read_text())["warnings"] == []
    assert "private diagnostic" not in capsys.readouterr().out


def test_latest_runtime_warnings_exclude_watchdog_feedback(monkeypatch, tmp_path):
    monkeypatch.setattr(server_health_monitor, "ROOT", tmp_path)
    monkeypatch.setattr(server_health_monitor, "inspect_services", lambda: [])
    monkeypatch.setattr(server_health_monitor, "inspect_backups", lambda _: [])
    notify = Mock(return_value="sent")
    monkeypatch.setattr(server_health_monitor, "notify", notify)
    response = Mock()
    response.status = 200
    response.read.return_value = b'{"status":"ok"}'
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(server_health_monitor, "urlopen", Mock(return_value=response))
    events = [
        {"event": "operational_snapshot", "operations": {"warnings": ["disk_low"]}},
        {
            "event": "operational_snapshot",
            "operations": {
                "warnings": [
                    "scheduler_stale",
                    "host_monitor_warning",
                    "host_monitor_stale",
                    "backup_missing_or_stale",
                    "private diagnostic",
                ]
            },
        },
        {"event": "operational_snapshot", "operations": None},
    ]
    monkeypatch.setattr(
        server_health_monitor.subprocess,
        "run",
        Mock(
            return_value=subprocess.CompletedProcess(
                [], 0, "\n".join(map(json.dumps, events))
            )
        ),
    )
    server_health_monitor.main()
    notify.assert_called_once_with(tmp_path, ["scheduler_stale"])
