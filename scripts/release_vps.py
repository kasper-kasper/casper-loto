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

ROOT = Path(__file__).resolve().parents[1]
ALL_SERVICES = ("api", "bot", "gateway")
FRONTENDS = (
    ROOT / "frontend" / "miniapp",
    ROOT / "frontend" / "admin",
    ROOT / "frontend" / "web",
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
    print(f"Release plan: {plan} -> health -> Docker cache maintenance")
    if args.dry_run:
        return

    if includes_gateway:
        build_frontends()

    remote_archive = f"/tmp/k-loto-release-{uuid4().hex}.tar.gz"
    with tempfile.TemporaryDirectory(prefix="k-loto-release-") as directory:
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
            compose = (
                "docker compose --env-file .env.production -f docker-compose.prod.yml"
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
            backend_services = [item for item in services if item != "gateway"]
            if backend_services:
                run_remote(
                    client,
                    "Backend image build",
                    f"cd /opt/k-loto && {compose} build --quiet "
                    + " ".join(backend_services),
                    timeout=1_800,
                )
            if includes_gateway:
                run_remote(
                    client,
                    "Gateway image assembly",
                    "cd /opt/k-loto && docker build --quiet "
                    "-f frontend/Dockerfile.prebuilt -t k-loto-gateway:latest .",
                    timeout=300,
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
                "Service restart",
                f"cd /opt/k-loto && {compose} up -d --no-build " + " ".join(services),
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
            run_remote(
                client,
                "Docker build-cache maintenance",
                "docker builder prune --all --force --keep-storage 2GB >/dev/null",
                timeout=300,
            )
            run_remote(
                client,
                "Old unused K-Loto image maintenance",
                "docker image prune --all --force --filter 'until=48h' "
                "--filter 'label=com.docker.compose.project=k-loto' >/dev/null",
                timeout=300,
            )
        finally:
            client.close()


if __name__ == "__main__":
    main()
