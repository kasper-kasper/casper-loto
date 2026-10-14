"""Release snapshots isolate old files and preserve untouched service assets."""

import hashlib
import tarfile
from pathlib import Path

import pytest
from scripts.release_snapshot import (
    backup,
    managed_path,
    prepare,
    promote,
    record,
    verify,
)


def put(root: Path, relative: str, data: bytes) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def test_exact_snapshot_excludes_stale_source_and_backend_only_preserves_clients(
    tmp_path,
):
    root = tmp_path / "project"
    (root / ".maintenance").mkdir(parents=True)
    old = {
        "backend/src/obsolete.py": put(root, "backend/src/obsolete.py", b"old"),
        "frontend/miniapp/dist/index.html": put(
            root, "frontend/miniapp/dist/index.html", b"active-client"
        ),
    }
    record(root, old)
    expected = {"backend/src/app.py": put(root, "backend/src/app.py", b"current")}
    stage = root / ".maintenance/candidate-test"
    assert prepare(root, stage, expected) == []
    assert not (stage / "backend/src/obsolete.py").exists()
    verify(stage, expected)
    promote(root, stage, expected)
    record(root, expected)
    assert not (root / "backend/src/obsolete.py").exists()
    assert (root / "frontend/miniapp/dist/index.html").read_bytes() == b"active-client"


def test_changed_artifact_fails_before_publication(tmp_path):
    root = tmp_path / "project"
    (root / ".maintenance").mkdir(parents=True)
    expected = {"app.py": put(root, "app.py", b"safe")}
    stage = root / ".maintenance/candidate-test"
    prepare(root, stage, expected)
    (stage / "app.py").write_bytes(b"altered")
    with pytest.raises(RuntimeError, match="hash mismatch"):
        promote(root, stage, expected)
    assert (root / "app.py").read_bytes() == b"safe"


def test_source_backup_preserves_owned_files_without_runtime_or_secrets(tmp_path):
    root = tmp_path / "project"
    (root / ".maintenance").mkdir(parents=True)
    expected = {"app.py": put(root, "app.py", b"old-source")}
    put(root, ".env.production", b"private")
    put(root, ".maintenance/runtime.json", b"runtime")
    archive = backup(root, expected)
    with tarfile.open(archive) as package:
        assert package.getnames() == ["app.py"]
        assert package.extractfile("app.py").read() == b"old-source"


def test_snapshot_accepts_only_known_public_environment_templates(tmp_path):
    assert managed_path(tmp_path, "frontend/miniapp/.env.example") == (
        tmp_path / "frontend/miniapp/.env.example"
    )
    with pytest.raises(RuntimeError, match="Secrets"):
        managed_path(tmp_path, "frontend/miniapp/.env.production")


@pytest.mark.parametrize(
    "relative",
    [
        "../elsewhere",
        "/etc/passwd",
        ".env.production",
        ".maintenance/data",
        "backups/dump",
        "frontend/web/package.json",
    ],
)
def test_source_snapshot_rejects_secrets_runtime_data_web_and_escape(
    tmp_path, relative
):
    with pytest.raises(RuntimeError):
        managed_path(tmp_path, relative)
