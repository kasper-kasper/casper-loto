"""Run the current identity code in an isolated disposable VPS database."""

from pathlib import Path
from uuid import uuid4

import paramiko
from release_vps import load_local_env, run_remote

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    env = load_local_env(ROOT / ".env")
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(
        env["SERVER_HOST"],
        username=env["SERVER_USER"],
        password=env["SERVER_PASSWORD"],
        timeout=20,
    )
    folder = "/opt/k-loto/.tools/web-identity-smoke-" + uuid4().hex
    compose = "docker compose --env-file .env.production -f docker-compose.prod.yml"
    created = False
    try:
        with client.open_sftp() as sftp:
            for directory in ("/opt/k-loto/.tools", folder):
                try:
                    sftp.mkdir(directory)
                except OSError:
                    sftp.stat(directory)
            files = list((ROOT / "backend/src").rglob("*.py"))
            for source in files:
                relative = source.relative_to(ROOT / "backend/src")
                target = folder + "/" + relative.as_posix()
                parents = relative.parent.parts
                current = folder
                for part in parents:
                    current += "/" + part
                    try:
                        sftp.mkdir(current)
                    except OSError:
                        sftp.stat(current)
                sftp.put(str(source), target)
            sftp.put(str(ROOT / "scripts/web_identity_smoke.py"), folder + "/smoke.py")
        run_remote(
            client,
            "Create isolated identity test database",
            f"cd /opt/k-loto && {compose} exec -T db sh -c "
            "'createdb -U \"$POSTGRES_USER\" k_loto_web_smoke'",
        )
        created = True
        run_remote(
            client,
            "PostgreSQL identity concurrency test",
            f"cd /opt/k-loto && {compose} run --rm --no-deps "
            f"-v {folder}:/audit:ro -e PYTHONPATH=/audit api sh -c '"
            'export DATABASE_URL="${DATABASE_URL%/*}/k_loto_web_smoke"; '
            "export SCHEDULER_ENABLED=false; python /audit/smoke.py'",
            timeout=180,
        )
    finally:
        if created:
            run_remote(
                client,
                "Remove disposable identity test database",
                f"cd /opt/k-loto && {compose} exec -T db sh -c "
                "'dropdb -U \"$POSTGRES_USER\" k_loto_web_smoke'",
            )
        client.close()


if __name__ == "__main__":
    main()
