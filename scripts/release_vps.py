"""Build, back up, migrate and publish one K-Loto release from the current commit."""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
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


def _npm_command() -> str:
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm:
        return npm
    portable = next((ROOT / ".tools" / "node").glob("node-v*-win-x64/npm.cmd"), None)
    if portable:
        return str(portable)
    raise RuntimeError("Node.js/npm is required to build the web interfaces.")


def build_frontends() -> None:
    """Build web assets locally so the small VPS never runs TypeScript."""
    npm = _npm_command()
    process_env = {
        **os.environ,
        "PATH": str(Path(npm).parent) + os.pathsep + os.environ.get("PATH", ""),
    }
    for frontend in FRONTENDS:
        if not (frontend / "node_modules").is_dir():
            print(f"Installing dependencies for {frontend.name}...", flush=True)
            subprocess.run([npm, "ci"], cwd=frontend, check=True, env=process_env)
        print(f"Building {frontend.name} locally...", flush=True)
        subprocess.run([npm, "run", "build"], cwd=frontend, check=True, env=process_env)
        if not (frontend / "dist" / "index.html").is_file():
            raise RuntimeError(f"Frontend build is missing: {frontend / 'dist'}")


def create_release_archive(target: Path, *, include_frontends: bool) -> None:
    """Create a git-clean release archive and optionally add built web assets."""
    raw_tar = target.with_suffix("")
    with raw_tar.open("wb") as stream:
        subprocess.run(
            ["git", "archive", "--format=tar", "HEAD"],
            cwd=ROOT,
            stdout=stream,
            check=True,
        )
    if include_frontends:
        with tarfile.open(raw_tar, "a") as archive:
            for frontend in FRONTENDS:
                archive.add(
                    frontend / "dist",
                    arcname=f"frontend/{frontend.name}/dist",
                )
    with (
        raw_tar.open("rb") as source,
        gzip.open(target, "wb", compresslevel=6) as output,
    ):
        shutil.copyfileobj(source, output)
    raw_tar.unlink()


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


def verify_candidate_finances(client: paramiko.SSHClient, compose: str) -> None:
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
        "-e SCHEDULER_ENABLED=false api sh -c '"
        f'export DATABASE_URL="${{DATABASE_URL%/*}}/{database}"; '
        "alembic upgrade head >/dev/null && alembic check && "
        "python -m scripts.financial_recovery_postgres_smoke && "
        "python -m scripts.integrity_delivery_postgres_smoke'"
    )
    run_remote(
        client, "Candidate financial database verification", command, timeout=600
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--services", nargs="+", choices=ALL_SERVICES, default=list(ALL_SERVICES)
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run:
        subprocess.run(["git", "diff", "--quiet"], cwd=ROOT, check=True)
        subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=True)
    env = {**load_local_env(ROOT / ".env"), **os.environ}
    required = ("SERVER_HOST", "SERVER_USER", "SERVER_PASSWORD")
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise SystemExit("Missing local deployment settings: " + ", ".join(missing))
    services = list(dict.fromkeys(args.services))
    includes_gateway = "gateway" in services
    plan = "local web build -> " if includes_gateway else ""
    plan += "backup -> upload -> build " + ", ".join(services)
    if any(item != "gateway" for item in services):
        plan += " -> migrate"
    print(f"Release plan: {plan} -> health (daily maintenance is separate)")
    if args.dry_run:
        return

    if includes_gateway:
        build_frontends()

    remote_archive = f"/tmp/k-loto-release-{uuid4().hex}.tar.gz"
    with tempfile.TemporaryDirectory(
        prefix="k-loto-release-", dir=ROOT / ".tools"
    ) as directory:
        archive = Path(directory) / "release.tar.gz"
        create_release_archive(archive, include_frontends=includes_gateway)
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
                compose = (
                    "docker compose --env-file .env.production "
                    "-f docker-compose.prod.yml"
                )
                run_remote(
                    client,
                    "Production database backup",
                    "cd /opt/k-loto && sh scripts/backup_production.sh",
                    timeout=300,
                )
                with client.open_sftp() as sftp:
                    sftp.put(str(archive), remote_archive)
                run_remote(
                    client,
                    "Release upload",
                    "set -eu; rm -rf -- /opt/k-loto/frontend/admin/dist "
                    "/opt/k-loto/frontend/miniapp/dist /opt/k-loto/frontend/web/dist; "
                    f"tar -xzf {remote_archive} -C /opt/k-loto; "
                    f"rm -f {remote_archive}",
                    timeout=120,
                )
                rollback_stamp = int(time.time())
                for service in services:
                    run_remote(
                        client,
                        f"Preserve {service} rollback image",
                        "docker image tag "
                        "$(docker inspect --format '{{.Image}}' "
                        f"k-loto-{service}-1) "
                        f"k-loto-{service}:before-release-{rollback_stamp}",
                    )
                backend_services = [item for item in services if item != "gateway"]
                if backend_services:
                    run_remote(
                        client,
                        "Backend image build",
                        f"cd /opt/k-loto && {compose} build --quiet "
                        + " ".join(backend_services),
                        timeout=1_800,
                    )
                    if "api" in backend_services:
                        verify_candidate_finances(client, compose)
                if includes_gateway:
                    run_remote(
                        client,
                        "Gateway image assembly",
                        "cd /opt/k-loto && docker build --quiet "
                        "-f frontend/Dockerfile.prebuilt -t k-loto-gateway:latest .",
                        timeout=300,
                    )
                    run_remote(
                        client,
                        "Validate gateway configuration",
                        f"cd /opt/k-loto && {compose} run --rm --no-deps gateway "
                        "caddy validate --config /etc/caddy/Caddyfile",
                        timeout=60,
                    )
                    run_remote(
                        client,
                        "Remove retired browser client from production checkout",
                        "rm -rf -- /opt/k-loto/frontend/web",
                        timeout=60,
                    )
                if backend_services:
                    run_remote(
                        client,
                        "Database migration",
                        f"cd /opt/k-loto && {compose} up -d db && "
                        f"{compose} run --rm api alembic upgrade head",
                        timeout=300,
                    )
                run_remote(
                    client,
                    "Preserve API and bot diagnostic logs",
                    "cd /opt/k-loto && python3 -c "
                    "'from scripts.server_maintenance import archive_diagnostic_logs; "
                    "archive_diagnostic_logs()'",
                    timeout=300,
                )
                run_remote(
                    client,
                    "Service restart",
                    f"cd /opt/k-loto && {compose} up -d --no-build "
                    + " ".join(services),
                    timeout=300,
                )
                if backend_services:
                    run_remote(
                        client,
                        "Migration and backup validation",
                        f"cd /opt/k-loto && {compose} exec -T api alembic check && "
                        f"{compose} exec -T db sh -c "
                        "'latest=$(ls -1t /backups/k-loto-*.dump | head -n 1); "
                        'test -n "$latest"; pg_restore --list "$latest" >/dev/null\'',
                        timeout=300,
                    )
                run_remote(
                    client,
                    "Production health",
                    "set -eu; cd /opt/k-loto; attempt=0; "
                    f"until {compose} exec -T api python -c "
                    '"import urllib.request; '
                    "urllib.request.urlopen('http://localhost:8000/health', timeout=3)"
                    + '" >/dev/null 2>&1; do '
                    "attempt=$((attempt + 1)); "
                    'test "$attempt" -lt 30 || exit 1; sleep 2; done; '
                    f"{compose} ps",
                    timeout=120,
                )
                if includes_gateway:
                    run_remote(
                        client,
                        "Public HTTPS and retired web verification",
                        "cd /opt/k-loto && "
                        "python3 scripts/verify_production_release.py",
                        timeout=300,
                    )
                if "api" in services:
                    run_remote(
                        client,
                        "Independent host monitoring",
                        "set -eu; cd /opt/k-loto; "
                        "install -d -m 755 /opt/k-loto/.monitoring; "
                        "install -m 644 "
                        "infrastructure/systemd/k-loto-health-monitor.service "
                        "/etc/systemd/system/k-loto-health-monitor.service; "
                        "install -m 644 "
                        "infrastructure/systemd/k-loto-health-monitor.timer "
                        "/etc/systemd/system/k-loto-health-monitor.timer; "
                        "systemctl daemon-reload; "
                        "systemctl enable --now k-loto-health-monitor.timer; "
                        "systemctl start k-loto-health-monitor.service",
                        timeout=60,
                    )
        finally:
            client.close()


if __name__ == "__main__":
    main()
