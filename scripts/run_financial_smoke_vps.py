"""Check candidate source in an isolated VPS database before publishing it."""

import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
from uuid import uuid4

import paramiko

from scripts.release_vps import load_local_env, run_remote
from scripts.vps_operation_lock import remote_operations_lock

ROOT = Path(__file__).resolve().parents[1]


def main():
    env = {**load_local_env(ROOT / ".env"), **os.environ}
    token = uuid4().hex[:12]
    database = f"k_loto_audit_stage1_{token}"
    candidate = f"/opt/k-loto/.audit-stage1-{token}"
    remote_archive = candidate + ".tar.gz"
    compose = "docker compose --env-file .env.production -f docker-compose.prod.yml"
    # Include new, uncommitted candidate files; never include .env or other secrets.
    listed = subprocess.check_output(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "backend",
            "scripts",
            "infrastructure",
            "alembic.ini",
            "pyproject.toml",
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    with tempfile.TemporaryDirectory(
        dir=ROOT / ".tools", prefix="audit-stage1-"
    ) as temp:
        archive_path = Path(temp) / "candidate.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            for name in listed:
                archive.add(ROOT / name, arcname=name)
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.connect(
            env["SERVER_HOST"],
            username=env["SERVER_USER"],
            password=env["SERVER_PASSWORD"],
            timeout=20,
        )
        try:
            client.get_transport().set_keepalive(15)
            with remote_operations_lock(client):
                with client.open_sftp() as sftp:
                    sftp.put(str(archive_path), remote_archive)
                command = (
                    "set -eu; cd /opt/k-loto; "
                    f"mkdir {candidate}; tar -xzf {remote_archive} -C {candidate}; "
                    "created=0; cleanup() { "
                    'if [ "$created" = 1 ]; then '
                    f"{compose} exec -T db sh -c '"
                    f'dropdb -U "$POSTGRES_USER" {database}\'; fi; '
                    f"rm -rf -- {candidate}; rm -f -- {remote_archive}; "
                    "}; trap cleanup EXIT; "
                    f"{compose} exec -T db sh -c '"
                    f'createdb -U "$POSTGRES_USER" {database}\'; '
                    "created=1; "
                    f"{compose} exec -T db sh -c '"
                    '(pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --schema-only; '
                    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
                    "--data-only --table=alembic_version) | "
                    f'psql -U "$POSTGRES_USER" -d {database} '
                    "-v ON_ERROR_STOP=1 >/dev/null'; "
                    f"{compose} run --rm --no-deps -v {candidate}:/candidate:ro "
                    "-w /candidate -e PYTHONPATH=/candidate/backend/src:/candidate "
                    "-e APP_ENV=test -e SCHEDULER_ENABLED=false api sh -c '"
                    f'export DATABASE_URL="${{DATABASE_URL%/*}}/{database}"; '
                    "alembic upgrade head >/dev/null && "
                    "alembic check && "
                    "python -m scripts.financial_recovery_postgres_smoke && "
                    "python -m scripts.integrity_delivery_postgres_smoke && "
                    "python -m unittest backend.tests.test_server_maintenance -q'"
                )
                run_remote(
                    client,
                    "Isolated candidate PostgreSQL regressions",
                    command,
                    timeout=600,
                )
        finally:
            client.close()


if __name__ == "__main__":
    main()
