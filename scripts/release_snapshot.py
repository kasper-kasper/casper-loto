"""Create and promote a verified source snapshot; never touch runtime data."""

import hashlib
import json
import os
import shutil
import sys
import tarfile
import time
from pathlib import Path, PurePosixPath


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def managed_path(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative).parts
    if (
        not parts
        or relative.startswith("/")
        or any(part in ("..", ".") for part in parts)
    ):
        raise RuntimeError("Invalid release path")
    if parts[0] in (
        ".git",
        ".maintenance",
        ".monitoring",
        "backups",
        ".tools",
        ".tmp",
        "design",
        "archive",
    ):
        raise RuntimeError("Runtime or unrelated files cannot be release inputs")
    if relative.startswith("frontend/web/") or relative == "frontend/web":
        raise RuntimeError("Web is not a release target")
    if any(part.startswith(".env") for part in parts) and relative not in (
        ".env.example",
        "frontend/miniapp/.env.example",
        "frontend/miniapp/.env.browser",
        "frontend/miniapp/.env.telegram",
    ):
        raise RuntimeError("Secrets cannot be release inputs")
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise RuntimeError("Release path escapes its root")
    for ancestor in (path, *path.parents):
        if ancestor == root.parent:
            break
        if ancestor.is_symlink():
            raise RuntimeError("Unexpected release symlink")
    return path


def prepare(root: Path, stage: Path, expected: dict[str, str]) -> list[str]:
    if stage.exists() or not stage.resolve().is_relative_to(
        (root / ".maintenance").resolve()
    ):
        raise RuntimeError("Snapshot must be a new owned maintenance directory")
    stage.mkdir()
    missing = []
    for relative, value in expected.items():
        source = managed_path(root, relative)
        target = managed_path(stage, relative)
        if not source.is_file() or digest(source) != value:
            missing.append(relative)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return missing


def verify(stage: Path, expected: dict[str, str]) -> None:
    for relative, value in expected.items():
        if digest(managed_path(stage, relative)) != value:
            raise RuntimeError(f"Release hash mismatch: {relative}")
    actual = {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}
    if actual != set(expected):
        raise RuntimeError("Snapshot contains unexpected files")


def promote(root: Path, stage: Path, expected: dict[str, str]) -> None:
    verify(stage, expected)
    previous_file = root / ".maintenance/current-release.json"
    if previous_file.is_symlink():
        raise RuntimeError("Invalid release record")
    previous = json.loads(previous_file.read_text()) if previous_file.exists() else {}
    for relative, value in expected.items():
        destination = managed_path(root, relative)
        if destination.is_file() and digest(destination) == value:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".release-new")
        if temporary.exists() or temporary.is_symlink():
            raise RuntimeError("Unexpected publication temporary file")
        shutil.copyfile(managed_path(stage, relative), temporary)
        os.replace(temporary, destination)
    # Only previously recorded source files belong to this cleanup. User files,
    # backups, secrets and business data cannot enter the managed namespace.
    for relative in set(previous) - set(expected):
        if preserved_client_asset(relative, expected):
            continue
        destination = managed_path(root, relative)
        if destination.is_file():
            if digest(destination) != previous[relative]:
                raise RuntimeError(
                    f"Obsolete managed file changed independently: {relative}"
                )
            destination.unlink()
    for relative, value in expected.items():
        if digest(managed_path(root, relative)) != value:
            raise RuntimeError("Promoted source verification failed")


def record(root: Path, expected: dict[str, str]) -> None:
    path = root / ".maintenance/current-release.json"
    temporary = path.with_suffix(".new")
    if path.is_symlink() or temporary.exists() or temporary.is_symlink():
        raise RuntimeError("Invalid release record destination")
    previous = json.loads(path.read_text()) if path.exists() else {}
    effective = {
        relative: value
        for relative, value in previous.items()
        if preserved_client_asset(relative, expected)
    }
    effective.update(expected)
    temporary.write_text(json.dumps(effective, sort_keys=True))
    os.replace(temporary, path)


def backup(root: Path, expected: dict[str, str]) -> Path:
    """Archive only release-owned source/assets, excluding credentials and data."""
    directory = root / "backups"
    if directory.is_symlink():
        raise RuntimeError("Invalid source backup directory")
    directory.mkdir(mode=0o700, exist_ok=True)
    destination = directory / f"release-before-{time.time_ns()}.tar.gz"
    temporary = destination.with_suffix(".partial")
    previous_path = root / ".maintenance/current-release.json"
    if previous_path.is_symlink():
        raise RuntimeError("Invalid release record")
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    with tarfile.open(temporary, "w:gz", compresslevel=1) as package:
        for relative in sorted(set(previous) | set(expected)):
            source = managed_path(root, relative)
            if source.is_file():
                package.add(source, arcname=relative, recursive=False)
    temporary.chmod(0o600)
    with tarfile.open(temporary) as package:
        if not package.getmembers():
            raise RuntimeError("Empty source backup")
    os.replace(temporary, destination)
    return destination


def preserved_client_asset(relative: str, expected: dict[str, str]) -> bool:
    for client in ("miniapp", "admin"):
        prefix = f"frontend/{client}/dist/"
        if relative.startswith(prefix) and prefix + "index.html" not in expected:
            return True
    return False


if __name__ == "__main__":
    root = Path("/opt/k-loto")
    mode, identifier = sys.argv[1:]
    if not identifier.isalnum():
        raise RuntimeError("Invalid release identity")
    stage = root / ".maintenance" / ("candidate-" + identifier)
    manifest = root / ".maintenance" / ("targets-" + identifier + ".json")
    maintenance = root / ".maintenance"
    if maintenance.is_symlink() or not maintenance.resolve().is_relative_to(
        root.resolve()
    ):
        raise RuntimeError("Maintenance path escapes the project")
    if mode == "cleanup":
        if stage.is_symlink():
            raise RuntimeError("Unexpected candidate symlink")
        if stage.exists():
            shutil.rmtree(stage)
        for path in (
            manifest,
            maintenance / ("missing-" + identifier + ".json"),
            maintenance / ("delta-" + identifier + ".tar.gz"),
            maintenance / ("release-helper-" + identifier + ".py"),
            maintenance / ("compose-" + identifier + ".json"),
        ):
            if path.is_symlink() or (path.exists() and not path.is_file()):
                raise RuntimeError("Unexpected transient path")
            path.unlink(missing_ok=True)
        sys.exit(0)
    expected = json.loads(manifest.read_text())
    if mode == "prepare":
        missing = prepare(root, stage, expected)
        (root / ".maintenance" / ("missing-" + identifier + ".json")).write_text(
            json.dumps(missing)
        )
    elif mode == "verify":
        verify(stage, expected)
    elif mode == "promote":
        promote(root, stage, expected)
    elif mode == "record":
        record(root, expected)
    elif mode == "backup":
        print(backup(root, expected).name)
    else:
        raise RuntimeError("Unknown release operation")
