"""Independent host watchdog; stores one redacted state file, never sends posts."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

ROOT = Path("/opt/k-loto")
CONTAINERS = ("k-loto-db-1", "k-loto-api-1", "k-loto-bot-1", "k-loto-gateway-1")


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
    warnings = inspect_services()
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
                    recent = True
            except ValueError:
                continue
        if not recent:
            warnings.append("runtime_monitor_stale")
    except (OSError, subprocess.SubprocessError):
        warnings.append("runtime_monitor_stale")
    report = {"checked_at": datetime.now(UTC).isoformat(), "warnings": warnings}
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
