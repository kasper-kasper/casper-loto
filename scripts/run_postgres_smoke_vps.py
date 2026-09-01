"""Run the destructive load smoke only in a disposable VPS PostgreSQL database."""

from __future__ import annotations

import os
from pathlib import Path

import paramiko
from release_vps import load_local_env

ROOT = Path(__file__).resolve().parents[1]


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
    compose = "docker compose --env-file .env.production -f docker-compose.prod.yml"
    command = (
        "set -eu; cd /opt/k-loto; "
        f"{compose} exec -T db sh -c '"
        'dropdb -U "$POSTGRES_USER" --if-exists k_loto_smoke; '
        'createdb -U "$POSTGRES_USER" k_loto_smoke\'; '
        "cleanup() { "
        f"{compose} exec -T db sh -c '"
        'dropdb -U "$POSTGRES_USER" --if-exists k_loto_smoke\' '
        ">/dev/null; }; "
        "trap cleanup EXIT; "
        f"{compose} run --rm api sh -c '"
        'export DATABASE_URL="${DATABASE_URL%/*}/k_loto_smoke"; '
        "alembic upgrade head >/dev/null; "
        "python scripts/postgres_e2e_smoke.py'"
    )
    try:
        _stdin, stdout, stderr = client.exec_command(command, timeout=900)
        output = stdout.read().decode("utf-8", "replace")
        error = stderr.read().decode("utf-8", "replace")
        exit_code = stdout.channel.recv_exit_status()
    finally:
        client.close()
    if exit_code:
        raise RuntimeError(
            f"PostgreSQL smoke failed (exit {exit_code}): {error[-2000:]}"
        )
    print(output.strip())


if __name__ == "__main__":
    main()
