"""Bounded VPS housekeeping. Default is a read-only plan; --apply is explicit."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
import tomllib
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path("/opt/k-loto")
CONFIG = ROOT / "infrastructure/server-maintenance.toml"
OPERATIONS_LOCK = Path("/run/lock/k-loto-operations.lock")
BACKUP_LOCK = Path("/run/lock/k-loto-backup.lock")
DATABASE_BACKUPS = Path("/var/lib/docker/volumes/k-loto_backups/_data")
DATABASE_DUMPS = {"database": re.compile(r"k-loto-\d{8}T\d{6}Z\.dump")}
REPOSITORIES = {"k-loto-api", "k-loto-bot", "k-loto-gateway"}
CONTAINERS = ("k-loto-db-1", "k-loto-api-1", "k-loto-bot-1", "k-loto-gateway-1")
ARCHIVES = {
    "miniapp": re.compile(r"miniapp-before-\d+\.\d+\.\d+-\d+\.tar\.gz"),
    "branding": re.compile(r"before-branding-\d+\.\d+\.\d+-\d+\.tar\.gz"),
    "maintenance": re.compile(r"maintenance-before-\d+\.tar\.gz"),
    "release": re.compile(
        r"(?:halloween|grand|aurora|vault|distribution(?:-followup)?|performance|release)-before-\d+\.tar\.gz"
    ),
    "audit": re.compile(
        r"(?:grand|aurora|vault|performance)-audit-before-\d+\.tar\.gz"
    ),
    "archive": re.compile(r"before-archive-\d+\.tar\.gz"),
    "devlog": re.compile(
        r"(?:distribution-devlog-before|DEVLOG-(?:halloween(?:-grid)?|pumpkin-field))-\d+\.md"
    ),
}
UPLOADS = {
    "release": re.compile(r"k-loto-release-[a-f0-9]{32}\.tar\.gz"),
    "miniapp": re.compile(r"miniapp-\d+\.\d+\.\d+-\d+\.tar\.gz"),
    "branding": re.compile(r"branding-\d+\.\d+\.\d+-\d+\.tar\.gz"),
    "maintenance": re.compile(r"maintenance-\d+\.tar\.gz"),
    "feature": re.compile(
        r"(?:halloween|grand|aurora|vault|distribution|performance)-\d+\.tar\.gz"
    ),
}
DIAGNOSTIC_LOGS = {
    service: re.compile(service + r"-\d{8}T\d{12}Z-[a-f0-9]{12}\.log\.gz")
    for service in ("api", "bot")
}

# Owner-approved retirement of editorial content, never lottery/financial history.
# Called under BOTH maintenance locks after verified off-host exports and quiescence.
EDITORIAL_RETIREMENT_SQL = """
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';
SELECT pg_advisory_xact_lock(hashtext('publication-event-engine'));
LOCK TABLE admin_audit_log IN ACCESS EXCLUSIVE MODE;
CREATE TEMP TABLE editorial_preserved_counts ON COMMIT DROP AS
SELECT (SELECT count(*) FROM tickets) tickets,
       (SELECT count(*) FROM draws) draws,
       (SELECT count(*) FROM ledger_transactions) ledger,
       (SELECT count(*) FROM admin_audit_log WHERE entity_type <> 'PUBLICATION') audit;
ALTER TABLE admin_audit_log DISABLE TRIGGER trg_admin_audit_immutable;
DELETE FROM admin_audit_log WHERE entity_type = 'PUBLICATION';
ALTER TABLE admin_audit_log ENABLE TRIGGER trg_admin_audit_immutable;
TRUNCATE TABLE publications, publication_event_states, interesting_facts,
               interesting_fact_batches, distribution_announcements;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM editorial_preserved_counts c WHERE
    c.tickets <> (SELECT count(*) FROM tickets) OR
    c.draws <> (SELECT count(*) FROM draws) OR
    c.ledger <> (SELECT count(*) FROM ledger_transactions) OR
    c.audit <> (SELECT count(*) FROM admin_audit_log
                WHERE entity_type <> 'PUBLICATION'))
  THEN RAISE EXCEPTION 'Protected business history changed'; END IF;
END $$;
COMMIT;
"""


def retire_editorial_data(archive_receipt: dict[str, Any]) -> dict[str, Any]:
    """Explicit one-off owner operation; caller has verified off-host archives."""
    if archive_receipt.get("authorization") != "channel-and-stories-removal-2026-10-19":
        raise RuntimeError("Missing owner authorization receipt")
    if not archive_receipt.get("local_archive_verified"):
        raise RuntimeError("Off-host archive must be verified first")
    for name in ("k-loto-api-1", "k-loto-bot-1"):
        if (
            run("docker", "inspect", "--format", "{{.State.Running}}", name).strip()
            != "false"
        ):
            raise RuntimeError("Quiesce API and bot before editorial retirement")
    subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "k-loto-db-1",
            "sh",
            "-c",
            'exec psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
        ],
        input=EDITORIAL_RETIREMENT_SQL,
        text=True,
        check=True,
        capture_output=True,
    )
    return {"editorial_data_retired": True, "business_history_preserved": True}


def delete_archived_editorial_file(path: Path, expected_sha256: str) -> bool:
    """Delete one exact archived file; no directory recursion or volume pruning."""
    import hashlib

    allowed_roots = (
        ROOT / "assets/publications",
        ROOT / "docs/publications",
        ROOT / "frontend/miniapp/public/assets/publications",
        ROOT / "frontend/admin/public/assets/publications",
        ROOT / "frontend/miniapp/dist/assets/publications",
        ROOT / "frontend/admin/dist/assets/publications",
        ROOT / "backups",
        Path("/opt/k-loto-backups"),
        DATABASE_BACKUPS,
        ROOT / ".maintenance/diagnostic-logs",
    )
    if not any(path.is_relative_to(root) for root in allowed_roots):
        raise RuntimeError("File outside editorial/archive scope")
    if path.is_symlink() or path.resolve() != path:
        raise RuntimeError("Refusing indirect editorial path")
    if not path.exists():
        return False
    info = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected_sha256:
        raise RuntimeError("Archived file changed; deletion refused")
    return delete_planned_file(
        FileCandidate(
            str(path),
            info.st_size,
            info.st_mtime_ns,
            info.st_dev,
            info.st_ino,
        )
    )


def retire_archived_editorial_images(receipt: dict[str, Any]) -> dict[str, Any]:
    """Remove exact archived app images and their content-bearing legacy layers."""
    if not receipt.get("local_archive_verified"):
        raise RuntimeError("Verified off-host image archive required")
    roots = receipt.get("archived_images", [])
    if not roots:
        raise RuntimeError("No archived app image identities")
    targets: set[str] = set()
    for row in roots:
        identifier = row["id"]
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", identifier):
            raise RuntimeError("Invalid archived image identity")
        inspected = subprocess.run(
            ["docker", "image", "inspect", identifier],
            capture_output=True,
            text=True,
            check=False,
        )
        if inspected.returncode:
            continue
        image = json.loads(inspected.stdout)[0]
        if not scoped_image(image):
            raise RuntimeError("Archived image is no longer exclusively project-owned")
        history = [
            json.loads(line)
            for line in run(
                "docker",
                "image",
                "history",
                "--no-trunc",
                "--format",
                "{{json .}}",
                identifier,
            ).splitlines()
        ]
        positions = [
            i
            for i, item in enumerate(history)
            if any(
                target in item.get("CreatedBy", "")
                for target in ("publication-assets", "/srv/admin", "/srv/miniapp")
            )
        ]
        targets.add(identifier)
        if positions:
            targets.update(
                item["ID"]
                for item in history[: max(positions) + 1]
                if item["ID"].startswith("sha256:")
            )
    # Legacy builder descendants may retain a content layer even without tags.
    ids = run("docker", "image", "ls", "-aq", "--no-trunc").split()
    images = json.loads(run("docker", "image", "inspect", *sorted(set(ids))))
    targets.update(
        image["Id"]
        for image in images
        if image.get("Config", {}).get("WorkingDir")
        in {"/build/admin", "/build/miniapp"}
    )
    changed = True
    while changed:
        changed = False
        for image in images:
            if image.get("Parent") in targets and image["Id"] not in targets:
                targets.add(image["Id"])
                changed = True
    selected = {image["Id"]: image for image in images if image["Id"] in targets}
    for identifier, image in selected.items():
        if image.get("RepoTags") and not scoped_image(image):
            raise RuntimeError("Content-bearing layer has unrelated tags")
        if run("docker", "ps", "-aq", "--filter", "ancestor=" + identifier).strip():
            raise RuntimeError("Archived content image is still used by a container")
    removed = []
    while selected:
        parents = {image.get("Parent") for image in selected.values()}
        leaves = [key for key in selected if key not in parents]
        if not leaves:
            raise RuntimeError("Unexpected Docker legacy image graph")
        for identifier in leaves:
            present = subprocess.run(
                ["docker", "image", "inspect", identifier],
                capture_output=True,
                check=False,
            )
            if present.returncode:
                del selected[identifier]
                continue
            tags = selected[identifier].get("RepoTags") or []
            if tags:
                run("docker", "image", "rm", *tags)
            else:
                run("docker", "image", "rm", identifier)
            removed.append(identifier)
            del selected[identifier]
    return {"retired_editorial_image_records": len(removed)}


def private_directory(path: Path) -> None:
    if path.is_symlink():
        raise RuntimeError("Refusing symlink in maintenance state")
    path.mkdir(mode=0o700, exist_ok=True)
    path.chmod(0o700)


def prune_archived_editorial_cache(receipt: dict[str, Any]) -> dict[str, Any]:
    """Remove only explicit, archived content cache IDs; never general cache GC."""
    if not receipt.get("local_archive_verified"):
        raise RuntimeError("Verified off-host archive required")
    identifiers = receipt.get("archived_build_cache_ids", [])
    if any(not re.fullmatch(r"[a-z0-9]{16,64}", item) for item in identifiers):
        raise RuntimeError("Invalid exact cache identity")
    for identifier in identifiers:
        run(
            "docker",
            "builder",
            "prune",
            "--all",
            "--force",
            "--filter",
            "id=" + identifier,
        )
    return {"targeted_editorial_cache_records": len(identifiers)}


def write_state(path: Path, value: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write((json.dumps(value, indent=2) + "\n").encode())
            output.flush()
            os.fsync(output.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def archive_diagnostic_logs() -> dict[str, Any]:
    """Caller holds the operations lock. Save logs before rotation/recreation.

    This is diagnostic retention, not the permanent financial ledger in PostgreSQL.
    Never echo log contents, including command failure output.
    """
    state = ROOT / ".maintenance"
    private_directory(state)
    directory = state / "diagnostic-logs"
    private_directory(directory)
    cursors_path = state / "log-cursors.json"
    if cursors_path.is_symlink():
        raise RuntimeError("Refusing symlink in log cursors")
    cursors = json.loads(cursors_path.read_text()) if cursors_path.exists() else {}
    captured = []
    until = datetime.now(UTC)
    until_text = until.isoformat()
    stamp = until.strftime("%Y%m%dT%H%M%S%fZ")
    for service in DIAGNOSTIC_LOGS:
        container = f"k-loto-{service}-1"
        identifier = run("docker", "inspect", "--format", "{{.Id}}", container).strip()
        if not re.fullmatch(r"[a-f0-9]{64}", identifier):
            raise RuntimeError("Invalid diagnostic container identity")
        command = ["docker", "logs", "--timestamps", "--until", until_text]
        previous = cursors.get(service, {})
        if previous.get("id") == identifier:
            # Validate stored timestamp before forwarding it as a Docker argument.
            datetime.fromisoformat(previous["until"])
            command.extend(["--since", previous["until"]])
        command.append(container)
        destination = directory / f"{service}-{stamp}-{identifier[:12]}.log.gz"
        temporary: Path | None = None
        try:
            # Disk-backed streaming keeps memory bounded even for a full buffer.
            with tempfile.TemporaryFile(dir=directory) as raw:
                result = subprocess.run(
                    command, stdout=raw, stderr=subprocess.STDOUT, timeout=120
                )
                if result.returncode:
                    raise RuntimeError(f"Diagnostic log capture failed: {service}")
                size = raw.tell()
                if size:
                    raw.seek(0)
                    with tempfile.NamedTemporaryFile(
                        dir=directory, delete=False
                    ) as out:
                        temporary = Path(out.name)
                        with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as zipped:
                            shutil.copyfileobj(raw, zipped)
                        out.flush()
                        os.fsync(out.fileno())
                    temporary.replace(destination)
                    captured.append({"service": service, "bytes": size})
            cursors[service] = {"id": identifier, "until": until_text}
            write_state(cursors_path, cursors)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return {"status": "archived", "utc": until_text, "captured": captured}


@dataclass(frozen=True)
class FileCandidate:
    path: str
    size: int
    mtime_ns: int
    device: int
    inode: int


def select_files(
    directory: Path,
    patterns: dict[str, re.Pattern[str]],
    *,
    now: float,
    age_seconds: int,
    keep: int,
    extra_directories: tuple[Path, ...] = (),
) -> list[FileCandidate]:
    """Count across directories; select only regular files with one link."""
    groups: dict[str, list[tuple[Path, os.stat_result]]] = {}
    for folder in dict.fromkeys((directory, *extra_directories)):
        if folder.is_symlink() or not folder.is_dir():
            continue
        for item in folder.iterdir():
            category = next(
                (
                    key
                    for key, pattern in patterns.items()
                    if pattern.fullmatch(item.name)
                ),
                None,
            )
            if category is None:
                continue
            info = item.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                continue
            groups.setdefault(category, []).append((item, info))
    candidates = []
    for items in groups.values():
        items.sort(key=lambda pair: (pair[1].st_mtime_ns, str(pair[0])), reverse=True)
        for item, info in items[keep:]:
            if age_seconds > 0 and now - info.st_mtime < age_seconds:
                continue
            candidates.append(
                FileCandidate(
                    str(item),
                    info.st_size,
                    info.st_mtime_ns,
                    info.st_dev,
                    info.st_ino,
                )
            )
    return candidates


def delete_planned_file(candidate: FileCandidate) -> bool:
    """Revalidate identity immediately before unlink; never follow a symlink."""
    path = Path(candidate.path)
    if path.parent.is_symlink():
        return False
    parent_fd = (
        os.open(
            path.parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        if os.name == "posix"
        else None
    )
    try:
        info = (
            os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            if parent_fd is not None
            else path.lstat()
        )
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            return False
        if (info.st_size, info.st_mtime_ns, info.st_dev, info.st_ino) != (
            candidate.size,
            candidate.mtime_ns,
            candidate.device,
            candidate.inode,
        ):
            return False
        if parent_fd is not None:
            os.unlink(path.name, dir_fd=parent_fd)
        else:
            path.unlink()
        return True
    except FileNotFoundError:
        return False
    finally:
        if parent_fd is not None:
            os.close(parent_fd)


def image_time(image: dict[str, Any]) -> float:
    return datetime.fromisoformat(image["Created"].replace("Z", "+00:00")).timestamp()


def scoped_image(image: dict[str, Any]) -> bool:
    tags = image.get("RepoTags") or []
    if tags:
        return all(tag.rsplit(":", 1)[0] in REPOSITORIES for tag in tags)
    labels = image.get("Config", {}).get("Labels") or {}
    return labels.get("com.docker.compose.project") == "k-loto" and labels.get(
        "com.docker.compose.service"
    ) in {None, "api", "bot", "gateway"}


def image_candidates(
    images: list[dict[str, Any]],
    referenced: set[str],
    *,
    now: float,
    keep: int,
    age_seconds: int,
) -> list[dict[str, Any]]:
    protected = set(referenced)
    for repository in REPOSITORIES:
        previous = []
        for image in images:
            tags = [
                tag
                for tag in image.get("RepoTags") or []
                if tag.rsplit(":", 1)[0] == repository
            ]
            if f"{repository}:latest" in tags:
                protected.add(image["Id"])
            # A before-* tag records a version that was live before a publication.
            stamps = [
                int(tag.rsplit("-", 1)[1])
                for tag in tags
                if re.fullmatch(repository + r":before-[a-z][a-z-]*-\d+", tag)
            ]
            if stamps and image["Id"] not in referenced:
                previous.append((max(stamps), image["Id"]))
        previous.sort(reverse=True)
        protected.update(identifier for _, identifier in previous[: keep - 1])
    return [
        image
        for image in images
        if scoped_image(image)
        and image["Id"] not in protected
        and (age_seconds == 0 or now - image_time(image) >= age_seconds)
    ]


def database_backup_candidates(keep: int) -> list[FileCandidate]:
    """Only known dumps in the verified backup volume, never database data."""
    mount = run(
        "docker", "volume", "inspect", "--format", "{{.Mountpoint}}", "k-loto_backups"
    ).strip()
    if mount != str(DATABASE_BACKUPS) or DATABASE_BACKUPS.is_symlink():
        raise RuntimeError("Unexpected database backup volume; cleanup stopped")
    if not DATABASE_BACKUPS.is_dir():
        raise RuntimeError("Database backup directory unavailable")
    return select_files(
        DATABASE_BACKUPS, DATABASE_DUMPS, now=time.time(), age_seconds=0, keep=keep
    )


def validate_retained_database_backups(keep: int) -> None:
    all_copies = database_backup_candidates(0)
    surplus = {row.path for row in database_backup_candidates(keep)}
    for row in all_copies:
        if row.path not in surplus:
            # Inspect the dump TOC before discarding older recovery points.
            run(
                "docker",
                "exec",
                "k-loto-db-1",
                "pg_restore",
                "--list",
                "/backups/" + Path(row.path).name,
            )


def prune_database_backups() -> list[str]:
    """Caller holds BACKUP_LOCK; prune after atomic backup creation or maintenance."""
    keep = policy()["database_backup_keep"]
    candidates = database_backup_candidates(keep)
    if not candidates:
        return []
    validate_retained_database_backups(keep)
    return [row.path for row in candidates if delete_planned_file(row)]


def remove_planned_image(image: dict[str, Any], eligible: set[str]) -> bool:
    """Under operations lock, recheck tags/ownership and all container references."""
    if image["Id"] not in eligible:
        return False
    try:
        current = json.loads(run("docker", "image", "inspect", image["Id"]))[0]
    except subprocess.CalledProcessError as error:
        # Docker can automatically remove unused parents with their descendants.
        if "No such image" in (error.stderr or ""):
            return False
        raise
    if (
        not scoped_image(current)
        or set(current.get("RepoTags") or []) != set(image.get("RepoTags") or [])
        or image["Id"] in referenced_images()
    ):
        return False
    # No force: Docker also refuses deletion of an image required by a container.
    try:
        run("docker", "image", "rm", *(current.get("RepoTags") or [current["Id"]]))
    except subprocess.CalledProcessError as error:
        # Legacy intermediate images may be parents of protected rollback images.
        # Their required layers are not independent rollback versions.
        diagnostic = error.stderr or ""
        if "dependent child images" in diagnostic or "is being used by" in diagnostic:
            return False
        raise
    return True


def prune_build_cache(keep_mb: int, minimum_age_hours: int) -> None:
    command = ["docker", "builder", "prune", "--all", "--force"]
    if minimum_age_hours:
        command.extend(["--filter", f"until={minimum_age_hours}h"])
    command.extend(["--keep-storage", f"{keep_mb}MB"])
    run(*command, timeout=300)


def active_operation(arguments: list[str]) -> bool:
    if not arguments:
        return False
    command = Path(arguments[0]).name
    if command in {"pg_dump", "pg_restore", "docker-compose"}:
        return True
    if command == "docker":
        return any(
            word in arguments[1:]
            for word in (
                "build",
                "buildx",
                "up",
                "down",
                "restart",
                "create",
                "pull",
            )
        )
    return command == "tar" and any(
        "/opt/k-loto" in word
        or "/tmp/miniapp-" in word
        or "/tmp/branding-" in word
        or "/tmp/k-loto-release-" in word
        for word in arguments[1:]
    )


def busy_host() -> bool:
    for item in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            arguments = (
                item.read_bytes().decode(errors="replace").strip("\0").split("\0")
            )
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if active_operation(arguments):
            return True
    return False


@contextmanager
def lock(path: Path) -> Iterator[None]:
    import fcntl

    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def run(*arguments: str, timeout: int = 60) -> str:
    result = subprocess.run(
        arguments, check=True, capture_output=True, text=True, timeout=timeout
    )
    return result.stdout


def inspect_images() -> list[dict[str, Any]]:
    identifiers = set(run("docker", "image", "ls", "-aq", "--no-trunc").split())
    if not identifiers:
        return []
    return json.loads(run("docker", "image", "inspect", *sorted(identifiers)))


def referenced_images() -> set[str]:
    identifiers = run("docker", "container", "ls", "-aq").split()
    if not identifiers:
        return set()
    return set(run("docker", "inspect", "--format", "{{.Image}}", *identifiers).split())


def check_health() -> None:
    containers = json.loads(run("docker", "container", "inspect", *CONTAINERS))
    for container in containers:
        state = container["State"]
        if (
            not state["Running"]
            or state.get("Health", {}).get("Status", "healthy") != "healthy"
        ):
            raise RuntimeError("Project service unhealthy; maintenance stopped")
    run(
        "docker",
        "exec",
        "k-loto-api-1",
        "python",
        "-c",
        "import urllib.request; "
        "urllib.request.urlopen('http://localhost:8000/health', timeout=5)",
    )


def policy() -> dict[str, int]:
    values = tomllib.loads(CONFIG.read_text())
    minimum = {
        "cache_keep_mb": 128,
        "cache_min_age_hours": 0,
        "image_keep_versions": 3,
        "image_min_age_days": 0,
        "database_backup_keep": 7,
        "archive_keep_per_category": 3,
        "archive_min_age_days": 0,
        "upload_min_age_hours": 24,
        "publication_grace_minutes": 15,
        "disk_warning_percent": 50,
        "diagnostic_log_retention_days": 90,
    }
    for key, lowest in minimum.items():
        if type(values.get(key)) is not int or values[key] < lowest:
            raise ValueError(f"Invalid maintenance policy: {key}")
    if values["disk_warning_percent"] > 95:
        raise ValueError("Invalid disk warning threshold")
    return values


def maintain(*, apply: bool) -> dict[str, Any]:
    values = policy()
    now = time.time()
    check_health()
    # Also protect older deployment helpers which do not yet take the shared lock.
    recent = select_files(Path("/tmp"), UPLOADS, now=now, age_seconds=0, keep=0)
    if busy_host() or any(
        now - item.mtime_ns / 1e9 < values["publication_grace_minutes"] * 60
        for item in recent
    ):
        return {"status": "skipped", "reason": "publication_or_backup_in_progress"}
    files = select_files(
        ROOT / "backups",
        ARCHIVES,
        now=now,
        age_seconds=values["archive_min_age_days"] * 86400,
        keep=values["archive_keep_per_category"],
        extra_directories=(Path("/opt/k-loto-backups"),),
    )
    files += select_files(
        Path("/tmp"),
        UPLOADS,
        now=now,
        age_seconds=values["upload_min_age_hours"] * 3600,
        keep=0,
    )
    files += select_files(
        ROOT / ".maintenance/diagnostic-logs",
        DIAGNOSTIC_LOGS,
        now=now,
        age_seconds=values["diagnostic_log_retention_days"] * 86400,
        keep=3,
    )
    database_files = database_backup_candidates(values["database_backup_keep"])
    files += database_files
    images = image_candidates(
        inspect_images(),
        referenced_images(),
        now=now,
        keep=values["image_keep_versions"],
        age_seconds=values["image_min_age_days"] * 86400,
    )
    report: dict[str, Any] = {
        "status": "applied" if apply else "planned",
        "utc": datetime.now(UTC).isoformat(),
        "policy": values,
        "files": [asdict(item) for item in files],
        "images": [
            {"id": image["Id"], "tags": image.get("RepoTags")} for image in images
        ],
        "cache": {
            "retain_mb": values["cache_keep_mb"],
            "minimum_age_hours": values["cache_min_age_hours"],
        },
    }
    if not apply:
        return report
    before = shutil.disk_usage(ROOT)
    # If saving important logs fails, do not start any cleanup.
    report["diagnostic_archive"] = archive_diagnostic_logs()
    if database_files:
        validate_retained_database_backups(values["database_backup_keep"])
    removed = []
    for item in files:
        if busy_host():
            raise RuntimeError("Concurrent operation detected; maintenance stopped")
        if delete_planned_file(item):
            removed.append(item.path)
    removed_images = []
    # Recompute protection once under the operations lock. Check changed tags and
    # fresh container references before each removal, without rescanning all images.
    eligible = (
        {
            row["Id"]
            for row in image_candidates(
                inspect_images(),
                referenced_images(),
                now=time.time(),
                keep=values["image_keep_versions"],
                age_seconds=values["image_min_age_days"] * 86400,
            )
        }
        if images
        else set()
    )
    # Remove descendants first so unused intermediate parents can also expire.
    for image in sorted(images, key=image_time, reverse=True):
        if busy_host():
            raise RuntimeError("Concurrent operation detected; maintenance stopped")
        if remove_planned_image(image, eligible):
            removed_images.append(image["Id"])
    if busy_host():
        raise RuntimeError("Concurrent operation detected; maintenance stopped")
    prune_build_cache(values["cache_keep_mb"], values["cache_min_age_hours"])
    check_health()
    after = shutil.disk_usage(ROOT)
    report.update(
        removed_files=removed,
        removed_images=removed_images,
        free_bytes_before=before.free,
        free_bytes_after=after.free,
        reclaimed_bytes=max(0, after.free - before.free),
        health="passed",
        disk_warning=(after.used / after.total * 100 >= values["disk_warning_percent"]),
    )
    state = ROOT / ".maintenance"
    private_directory(state)
    write_state(state / "last-run.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--archive-logs", action="store_true")
    arguments = parser.parse_args()
    if arguments.apply and arguments.archive_logs:
        parser.error("Choose cleanup or diagnostic capture")
    if os.name != "posix" or ROOT.resolve() != ROOT or ROOT.is_symlink():
        raise SystemExit("Maintenance requires the configured Linux production root")
    try:
        with ExitStack() as stack:
            stack.enter_context(lock(OPERATIONS_LOCK))
            stack.enter_context(lock(BACKUP_LOCK))
            result = (
                archive_diagnostic_logs()
                if arguments.archive_logs
                else maintain(apply=arguments.apply)
            )
    except BlockingIOError:
        result = {"status": "skipped", "reason": "publication_or_backup_lock_held"}
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
