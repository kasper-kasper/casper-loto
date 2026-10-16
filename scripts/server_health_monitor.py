"""Independent host watchdog with redacted state and private owner alerts."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

if __package__:
    from scripts.owner_health_alert import notify
    from scripts.server_maintenance import database_backup_candidates
else:
    from owner_health_alert import notify
    from server_maintenance import database_backup_candidates

ROOT = Path("/opt/k-loto")
CONTAINERS = ("k-loto-db-1", "k-loto-api-1", "k-loto-bot-1", "k-loto-gateway-1")
RUNTIME_WARNINGS = {
    "overdue_draws",
    "delayed_publications",
    "scheduler_stale",
    "disk_low",
    "monitor_check_failed",
    "backup_retention_exceeded",
}


def inspect_backups(now: float) -> list[str]:
    warnings = []
    try:
        copies = [row for row in database_backup_candidates(0) if row.size > 0]
        latest = max((row.mtime_ns / 1e9 for row in copies), default=0)
        if not latest or now - latest > 26 * 3600 or latest > now + 300:
            warnings.append("backup_missing_or_stale")
    except Exception:
        warnings.append("backup_check_failed")
    try:
        result = subprocess.run(
            [
                "systemctl",
                "show",
                "k-loto-backup.service",
                "--property=Result",
                "--value",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        if result.stdout.strip() != "success":
            warnings.append("backup_job_failed")
    except (OSError, subprocess.SubprocessError):
        warnings.append("backup_job_check_failed")
    return warnings


def inspect_services() -> list[str]:
    warnings: list[str] = []
    for name in CONTAINERS:
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{json .State}}", name],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            state = json.loads(result.stdout)
            if (
                not state.get("Running")
                or state.get("Health", {}).get("Status") == "unhealthy"
            ):
                warnings.append(f"service_unhealthy:{name}")
        except (OSError, ValueError, subprocess.SubprocessError):
            warnings.append(f"service_unavailable:{name}")
    return warnings


def main() -> None:
    now = datetime.now(UTC)
    warnings = inspect_services() + inspect_backups(now.timestamp())
    try:
        url = os.environ.get(
            "K_LOTO_HEALTH_URL", "https://play.85.137.90.58.sslip.io:9443/health"
        )
        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read(4096))
            if response.status != 200 or payload.get("status") != "ok":
                warnings.append("public_health_failed")
    except Exception:
        warnings.append("public_health_failed")
    try:
        result = subprocess.run(
            ["docker", "logs", "--since", "3m", "--tail", "1000", "k-loto-api-1"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        recent = False
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
                if event.get("event") == "operational_snapshot":
                    # Only the newest snapshot counts; exclude watchdog feedback.
                    runtime_warnings = (
                        set(event.get("operations", {}).get("warnings", []))
                        & RUNTIME_WARNINGS
                    )
                    recent = True
            except (ValueError, AttributeError, TypeError):
                continue
        if not recent:
            warnings.append("runtime_monitor_stale")
        else:
            warnings.extend(sorted(runtime_warnings))
    except (OSError, subprocess.SubprocessError):
        warnings.append("runtime_monitor_stale")
    warnings = sorted(set(warnings))
    report = {
        "checked_at": now.isoformat(),
        "warnings": warnings,
        "owner_notification": notify(ROOT, warnings),
    }
    directory = ROOT / ".monitoring"
    directory.mkdir(mode=0o755, exist_ok=True)
    temporary = directory / "state.json.tmp"
    temporary.write_text(json.dumps(report), encoding="utf-8")
    temporary.chmod(0o644)
    temporary.replace(directory / "state.json")
    # JSON codes only; no Docker output, URL errors or environment values.
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
