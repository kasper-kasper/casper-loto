"""Build, back up, migrate and publish one K-Loto release from the current commit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import paramiko

if __package__:
    from scripts.vps_operation_lock import remote_operations_lock
else:
    from vps_operation_lock import remote_operations_lock

ROOT = Path(__file__).resolve().parents[1]
ALL_SERVICES = ("api", "bot", "gateway")
FRONTENDS = (
    ROOT / "frontend" / "miniapp",
    ROOT / "frontend" / "admin",
)


def load_local_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def build_frontends() -> None:
    """Build production clients in clean workspaces."""
    if __package__:
        from scripts.build_frontends import build
    else:
        from build_frontends import build
    build()


def _tail(buffer: bytearray, chunk: bytes, limit: int = 8_000) -> None:
    buffer.extend(chunk)
    if len(buffer) > limit:
        del buffer[:-limit]


def run_remote(
    client: paramiko.SSHClient,
    label: str,
    command: str,
    *,
    timeout: int = 900,
) -> str:
    """Run one visible release stage while draining both SSH output streams."""
    print(f"-> {label}", flush=True)
    _stdin, stdout, _stderr = client.exec_command(command, timeout=timeout)
    channel = stdout.channel
    output = bytearray()
    error = bytearray()
    deadline = time.monotonic() + timeout
    while True:
        progressed = False
        while channel.recv_ready():
            _tail(output, channel.recv(65_536))
            progressed = True
        while channel.recv_stderr_ready():
            _tail(error, channel.recv_stderr(65_536))
            progressed = True
        if (
            channel.exit_status_ready()
            and not channel.recv_ready()
            and not channel.recv_stderr_ready()
        ):
            break
        if time.monotonic() >= deadline:
            channel.close()
            raise TimeoutError(f"Remote stage '{label}' timed out after {timeout}s.")
        if not progressed:
            time.sleep(0.05)
    exit_code = channel.recv_exit_status()
    text_output = output.decode("utf-8", "replace")
    text_error = error.decode("utf-8", "replace")
    if exit_code:
        raise RuntimeError(
            f"Remote stage '{label}' failed (exit {exit_code}):\n"
            f"{text_error or text_output}"
        )
    if text_output.strip():
        print(text_output.strip(), flush=True)
    print(f"   {label}: OK", flush=True)
    return text_output


def verify_candidate_finances(
    client: paramiko.SSHClient, compose: str, *, service: str = "api"
) -> None:
    """Exercise the freshly built runtime without touching production business rows."""
    database = f"k_loto_audit_stage1_{uuid4().hex[:12]}"
    command = (
        "set -eu; cd /opt/k-loto; "
        f"{compose} exec -T db sh -c '"
        f'createdb -U "$POSTGRES_USER" {database}\'; '
        "cleanup() { "
        f"{compose} exec -T db sh -c '"
        f'dropdb -U "$POSTGRES_USER" {database}\'; '
        "}; trap cleanup EXIT; "
        f"{compose} exec -T db sh -c '"
        '(pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --schema-only; '
        'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
        "--data-only --table=alembic_version) | "
        f'psql -U "$POSTGRES_USER" -d {database} '
        "-v ON_ERROR_STOP=1 >/dev/null'; "
        f"{compose} run --rm --no-deps -e APP_ENV=test "
        f"-e SCHEDULER_ENABLED=false -e UV_CACHE_DIR=/tmp/uv-cache {service} sh -c '"
        f'export DATABASE_URL="${{DATABASE_URL%/*}}/{database}"; '
        "python -m scripts.verify_runtime_lock && "
        "uv sync --locked --extra dev --no-editable >/dev/null && "
        "pytest -q --disable-warnings --basetemp=/tmp/runtime-tests "
        "--ignore=backend/tests/test_web_api.py "
        "--ignore=backend/tests/test_web_identity.py && "
        "alembic upgrade head >/dev/null && alembic check && "
        "python -m scripts.financial_recovery_postgres_smoke && "
        "python -m scripts.integrity_delivery_postgres_smoke && "
        "python -m scripts.miniapp_integration_smoke'"
    )
    run_remote(
        client, "Candidate financial database verification", command, timeout=600
    )


def verify_empty_database(
    client: paramiko.SSHClient, compose: str, *, service: str
) -> None:
    database = f"k_loto_bootstrap_smoke_{uuid4().hex[:12]}"
    command = (
        "set -eu; cd /opt/k-loto; "
        f"{compose} exec -T db sh -c 'createdb -U \"$POSTGRES_USER\" {database}'; "
        f"cleanup() {{ {compose} exec -T db sh -c 'dropdb -U "
        f'"$POSTGRES_USER" {database}\'; }}; trap cleanup EXIT; '
        f"{compose} run --rm --no-deps -e APP_ENV=test -e "
        f"SCHEDULER_ENABLED=false {service} sh -c '"
        f'export DATABASE_URL="${{DATABASE_URL%/*}}/{database}"; '
        "python -m scripts.migrate_database --target 0051_distribution_results && "
        "python -m scripts.bootstrap_index_smoke && "
        "python -m scripts.migrate_database && alembic check'"
    )
    run_remote(
        client, "Empty database bootstrap and migration recovery", command, timeout=600
    )


def release_files(include_frontends: bool) -> dict[str, str]:
    paths = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    paths = [
        p
        for p in paths
        if p and not p.startswith("frontend/web/") and (ROOT / p).is_file()
    ]
    if include_frontends:
        if __package__:
            from scripts.build_frontends import verify_build
        else:
            from build_frontends import verify_build
        for client in ("miniapp", "admin"):
            verify_build(client)
            paths.extend(
                p.relative_to(ROOT).as_posix()
                for p in (ROOT / "frontend" / client / "dist").rglob("*")
                if p.is_file()
            )
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


def compatibility_chunks(client: paramiko.SSHClient) -> dict[str, str]:
    output = run_remote(
        client,
        "Read active gateway compatibility chunks",
        "docker exec k-loto-gateway-1 sh -c "
        + shlex.quote(
            "find /srv/miniapp/assets /srv/admin/assets -type f \\( "
            "-name '*.js' -o -name '*.css' \\) -exec sha256sum {} +"
        ),
    )
    result = {}
    for line in output.splitlines():
        value, relative = line.split(None, 1)
        relative = relative.strip().replace("/srv/", "frontend/", 1)
        relative = relative.replace(
            "frontend/miniapp/", "frontend/miniapp/dist/", 1
        ).replace("frontend/admin/", "frontend/admin/dist/", 1)
        if not re.fullmatch(
            r"frontend/(miniapp|admin)/dist/assets/[A-Za-z0-9_.-]+-[A-Za-z0-9_-]{6,}\.(js|css)",
            relative,
        ):
            raise RuntimeError("Unexpected compatibility chunk name")
        result[relative] = value
    return result


def wait_for_health(client: paramiko.SSHClient, compose: str) -> None:
    run_remote(
        client,
        "API health",
        "set -eu; attempt=0; until docker exec k-loto-api-1 python -c "
        + shlex.quote(
            "from urllib.request import urlopen; "
            "urlopen('http://localhost:8000/health',timeout=3)"
        )
        + " >/dev/null 2>&1; do attempt=$((attempt+1)); test "
        '"$attempt" -lt 45 || exit 1; sleep 2; done',
        timeout=150,
    )
    run_remote(
        client,
        "Public HTTPS, client hashes and retired Web",
        "cd /opt/k-loto && python3 scripts/verify_production_release.py",
        timeout=240,
    )
    run_remote(
        client,
        "Independent production monitoring",
        "systemctl start k-loto-health-monitor.service && cat "
        "/opt/k-loto/.monitoring/state.json",
        timeout=90,
    )


def schema_fingerprint(client: paramiko.SSHClient, compose: str) -> str:
    return run_remote(
        client,
        "Read schema fingerprint",
        "cd /opt/k-loto && "
        + compose
        + " exec -T db sh -c "
        + shlex.quote(
            '(pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --schema-only '
            '--no-owner --no-privileges | sed "/^\\\\restrict /d;'
            '/^\\\\unrestrict /d"; psql -U "$POSTGRES_USER" '
            '-d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version") '
            "| sha256sum"
        ),
    ).split()[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--services", nargs="+", choices=ALL_SERVICES, default=list(ALL_SERVICES)
    )
    parser.add_argument(
        "--reuse-built",
        action="store_true",
        help="Use only artifacts whose source/file hashes still verify",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    services = list(dict.fromkeys(args.services))
    gateway = "gateway" in services
    backend = [service for service in services if service != "gateway"]
    if args.dry_run:
        print(
            "Release: clean selected builds -> backup -> verified "
            "snapshot -> candidate checks -> migrate -> selected "
            "restart -> public health"
        )
        return
    subprocess.run(["git", "diff", "--quiet"], cwd=ROOT, check=True)
    subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=True)
    if gateway and not args.reuse_built:
        build_frontends()
    expected = release_files(gateway)
    local_inputs = set(expected)
    current_chunks = {
        p: value
        for p, value in expected.items()
        if re.fullmatch(r"frontend/(miniapp|admin)/dist/assets/[^/]+\.(js|css)", p)
    }
    env = {**load_local_env(ROOT / ".env"), **os.environ}
    missing = [
        key
        for key in ("SERVER_HOST", "SERVER_USER", "SERVER_PASSWORD")
        if not env.get(key)
    ]
    if missing:
        raise RuntimeError("Missing local deployment settings: " + ", ".join(missing))
    token = uuid4().hex
    maintenance = "/opt/k-loto/.maintenance"
    stage = maintenance + "/candidate-" + token
    targets = maintenance + "/targets-" + token + ".json"
    helper = maintenance + "/release-helper-" + token + ".py"
    archive_name = maintenance + "/delta-" + token + ".tar.gz"
    compose = "docker compose --env-file .env.production -f docker-compose.prod.yml"
    overlay = maintenance + "/compose-" + token + ".json"
    candidate_compose = compose + " -f " + overlay
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(
        env["SERVER_HOST"],
        username=env["SERVER_USER"],
        password=env["SERVER_PASSWORD"],
        timeout=20,
    )
    client.get_transport().set_keepalive(15)
    try:
        with remote_operations_lock(client):
            run_remote(
                client,
                "Database backup",
                "cd /opt/k-loto && sh scripts/backup_production.sh",
                timeout=300,
            )
            retained = []
            if gateway:
                active = compatibility_chunks(client)
                with client.open_sftp() as sftp:
                    try:
                        with sftp.open(
                            maintenance + "/gateway-compat.json", "rb"
                        ) as stream:
                            saved = json.loads(stream.read())
                            retained = [
                                saved["current"],
                                *saved.get("previous", [])[:1],
                            ]
                    except FileNotFoundError:
                        pass
                # Current active image plus one older owned set; never copy an
                # unverified arbitrary file into the gateway snapshot.
                retained = retained or [active]
                for group in retained:
                    if any(active.get(path) != value for path, value in group.items()):
                        raise RuntimeError(
                            "Gateway compatibility record does not match active image"
                        )
                for group in reversed(retained):
                    for path, value in group.items():
                        if path not in current_chunks:
                            expected[path] = value
            with client.open_sftp() as sftp:
                sftp.put(str(ROOT / "scripts/release_snapshot.py"), helper)
                with sftp.open(targets, "wb") as stream:
                    stream.write(json.dumps(expected))
                with sftp.open(overlay, "wb") as stream:
                    stream.write(
                        json.dumps(
                            {
                                "services": {
                                    name: {"image": f"k-loto-{name}:candidate-{token}"}
                                    for name in services
                                }
                            }
                        )
                    )

            def operation(mode: str) -> None:
                run_remote(
                    client,
                    "Snapshot " + mode,
                    "python3 " + shlex.quote(helper) + " " + mode + " " + token,
                    timeout=180,
                )

            try:
                operation("prepare")
                with client.open_sftp() as sftp:
                    with sftp.open(
                        maintenance + "/missing-" + token + ".json", "rb"
                    ) as stream:
                        changed = json.loads(stream.read())
                # Compatibility bytes must already match the active/prior release.
                if any(path not in local_inputs for path in changed):
                    raise RuntimeError(
                        "A retained compatibility chunk is missing or altered"
                    )
                (ROOT / ".tools").mkdir(exist_ok=True)
                with tempfile.TemporaryDirectory(
                    prefix="release-", dir=ROOT / ".tools"
                ) as directory:
                    archive = Path(directory) / "delta.tar.gz"
                    with tarfile.open(archive, "w:gz") as package:
                        for path in changed:
                            if (
                                hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                                != expected[path]
                            ):
                                raise RuntimeError(
                                    "Source changed during release packaging"
                                )
                            package.add(ROOT / path, arcname=path)
                    print(
                        json.dumps(
                            {
                                "snapshot_files": len(expected),
                                "transferred_files": len(changed),
                                "upload_bytes": archive.stat().st_size,
                            }
                        ),
                        flush=True,
                    )
                    with client.open_sftp() as sftp:
                        sftp.put(str(archive), archive_name)
                run_remote(
                    client,
                    "Populate exact candidate snapshot",
                    "tar -xzf "
                    + shlex.quote(archive_name)
                    + " -C "
                    + shlex.quote(stage),
                    timeout=180,
                )
                operation("verify")
                stamp = int(time.time())
                for service in services:
                    run_remote(
                        client,
                        "Preserve rollback " + service,
                        "docker image tag $(docker inspect --format '{{.Image}}' "
                        "k-loto-"
                        + service
                        + "-1) k-loto-"
                        + service
                        + ":before-release-"
                        + str(stamp),
                    )
                    dockerfile = (
                        "frontend/Dockerfile.prebuilt"
                        if service == "gateway"
                        else "backend/Dockerfile"
                    )
                    run_remote(
                        client,
                        "Build verified " + service,
                        "docker build --quiet -f "
                        + stage
                        + "/"
                        + dockerfile
                        + " -t k-loto-"
                        + service
                        + ":candidate-"
                        + token
                        + " "
                        + stage,
                        timeout=1800,
                    )
                if backend:
                    candidate_service = backend[0]
                    verify_candidate_finances(
                        client, candidate_compose, service=candidate_service
                    )
                    verify_empty_database(
                        client, candidate_compose, service=candidate_service
                    )
                    if set(backend) != {"api", "bot"}:
                        from alembic.config import Config
                        from alembic.script import ScriptDirectory

                        head = ScriptDirectory.from_config(
                            Config(str(ROOT / "alembic.ini"))
                        ).get_current_head()
                        current = run_remote(
                            client,
                            "Check shared schema compatibility",
                            "cd /opt/k-loto && "
                            + compose
                            + " exec -T db sh -c "
                            + shlex.quote(
                                'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
                                '-Atc "SELECT version_num FROM alembic_version"'
                            ),
                        ).strip()
                        if current != head:
                            raise RuntimeError(
                                "Pending shared migration requires API and bot "
                                "to be published together."
                            )
                if gateway:
                    run_remote(
                        client,
                        "Caddy validation",
                        "cd /opt/k-loto && "
                        + candidate_compose
                        + " run --rm --no-deps gateway caddy validate --config "
                        "/etc/caddy/Caddyfile",
                        timeout=60,
                    )
                # Build uses only the immutable candidate, never the overlaid mirror.
                # Publish the mirror once every image and preflight has passed.
                operation("backup")
                operation("promote")
                if backend:
                    before_schema = schema_fingerprint(client, compose)
                    run_remote(
                        client,
                        "Archive API/bot diagnostic logs",
                        "cd /opt/k-loto && python3 -c 'from "
                        "scripts.server_maintenance import "
                        "archive_diagnostic_logs; archive_diagnostic_logs()'",
                        timeout=300,
                    )
                    run_remote(
                        client,
                        "Quiesce affected workers",
                        "cd /opt/k-loto && "
                        + compose
                        + " stop -t 65 "
                        + " ".join(backend),
                        timeout=180,
                    )
                    try:
                        run_remote(
                            client,
                            "Production migration from selected candidate image",
                            "cd /opt/k-loto && "
                            + candidate_compose
                            + " run --rm --no-deps "
                            + backend[0]
                            + " python -m scripts.migrate_database",
                            timeout=300,
                        )
                    except Exception:
                        if schema_fingerprint(client, compose) != before_schema:
                            raise RuntimeError(
                                "Migration changed the schema before failing; "
                                "workers remain stopped for recovery review."
                            ) from None
                        for service in backend:
                            run_remote(
                                client,
                                "Restore compatible prior " + service,
                                "docker image tag k-loto-"
                                + service
                                + ":before-release-"
                                + str(stamp)
                                + " k-loto-"
                                + service
                                + ":latest",
                            )
                        run_remote(
                            client,
                            "Resume previous workers",
                            "cd /opt/k-loto && "
                            + compose
                            + " up -d --no-build --no-deps "
                            + " ".join(backend),
                            timeout=180,
                        )
                        raise
                for service in services:
                    run_remote(
                        client,
                        "Promote verified image " + service,
                        f"docker image tag k-loto-{service}:candidate-{token} "
                        f"k-loto-{service}:latest",
                    )
                run_remote(
                    client,
                    "Restart selected services",
                    "cd /opt/k-loto && "
                    + compose
                    + " up -d --no-build --no-deps "
                    + " ".join(services),
                    timeout=300,
                )
                wait_for_health(client, compose)
                run_remote(
                    client,
                    "Backup catalog validation",
                    "cd /opt/k-loto && "
                    + compose
                    + " exec -T db sh -c 'latest=$(ls -1t "
                    '/backups/k-loto-*.dump | head -n 1); test -n "$latest"; '
                    'pg_restore --list "$latest" >/dev/null\'',
                    timeout=180,
                )
                operation("record")
                if gateway:
                    with client.open_sftp() as sftp:
                        with sftp.open(
                            maintenance + "/gateway-compat.json", "wb"
                        ) as stream:
                            stream.write(
                                json.dumps(
                                    {"current": current_chunks, "previous": retained}
                                )
                            )
                run_remote(
                    client,
                    "Production service state",
                    "docker ps --format '{{.Names}} {{.Status}}'",
                )
            finally:
                # Exact owned transient names only; storage retention stays separate.
                operation("cleanup")
    finally:
        client.close()


if __name__ == "__main__":
    main()
