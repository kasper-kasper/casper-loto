"""Build, back up, migrate and publish one K-Loto release from the current commit."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

import paramiko

ROOT = Path(__file__).resolve().parents[1]
ALL_SERVICES = ("api", "bot", "gateway")


def load_local_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


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
    print(
        "Release plan: backup -> upload -> build "
        + ", ".join(services)
        + " -> migrate -> health"
    )
    if args.dry_run:
        return

    remote_archive = f"/tmp/k-loto-release-{uuid4().hex}.tar.gz"
    with tempfile.TemporaryDirectory(prefix="k-loto-release-") as directory:
        archive = Path(directory) / "release.tar.gz"
        with archive.open("wb") as stream:
            subprocess.run(
                ["git", "archive", "--format=tar.gz", "HEAD"],
                cwd=ROOT,
                stdout=stream,
                check=True,
            )
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
            with client.open_sftp() as sftp:
                sftp.put(str(archive), remote_archive)
            compose = (
                "docker compose --env-file .env.production -f docker-compose.prod.yml"
            )
            build = " ".join(services)
            command = (
                "set -eu; cd /opt/k-loto; sh scripts/backup_production.sh; "
                f"tar -xzf {remote_archive} -C /opt/k-loto; rm -f {remote_archive}; "
                f"{compose} build {build}; {compose} up -d db; "
                f"{compose} run --rm api alembic upgrade head; "
                f"{compose} up -d {build}; {compose} ps"
            )
            _stdin, stdout, stderr = client.exec_command(command, timeout=1800)
            exit_code = stdout.channel.recv_exit_status()
            output = stdout.read().decode("utf-8", "replace")
            error = stderr.read().decode("utf-8", "replace")
            if exit_code:
                raise RuntimeError(
                    f"Remote release failed (exit {exit_code}):\n{error[-4000:]}"
                )
            print(output[-4000:])
        finally:
            client.close()


if __name__ == "__main__":
    main()
