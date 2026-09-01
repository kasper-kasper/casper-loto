"""Download and verify the newest production PostgreSQL dump outside the VPS."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path

import paramiko
from release_vps import load_local_env

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "backups" / "offsite"


def main() -> None:
    env = {**load_local_env(ROOT / ".env"), **os.environ}
    required = ("SERVER_HOST", "SERVER_USER", "SERVER_PASSWORD")
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise SystemExit("Missing local deployment settings: " + ", ".join(missing))
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(
        env["SERVER_HOST"],
        username=env["SERVER_USER"],
        password=env["SERVER_PASSWORD"],
        timeout=20,
    )
    command = (
        "cd /opt/k-loto && "
        "docker compose --env-file .env.production -f docker-compose.prod.yml "
        "exec -T db sh -c 'latest=$(ls -1t /backups/k-loto-*.dump | head -n 1); "
        'test -n "$latest"; cat "$latest"\''
    )
    try:
        _stdin, stdout, stderr = client.exec_command(command, timeout=300)
        payload = stdout.read()
        error = stderr.read().decode("utf-8", "replace")
        exit_code = stdout.channel.recv_exit_status()
    finally:
        client.close()
    if exit_code or not payload.startswith(b"PGDMP"):
        raise RuntimeError(
            f"Backup download or format validation failed: {error[-500:]}"
        )
    DESTINATION.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = DESTINATION / f"k-loto-production-{timestamp}.dump"
    target.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    target.with_suffix(".dump.sha256").write_text(
        f"{digest}  {target.name}\n", encoding="ascii"
    )
    print(f"Verified off-VPS backup: {target.relative_to(ROOT)} ({len(payload)} bytes)")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
