"""Release snapshots isolate old files and preserve untouched service assets."""

import hashlib
import tarfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from scripts import release_vps
from scripts.release_snapshot import (
    backup,
    managed_path,
    prepare,
    promote,
    record,
    verify,
)


def test_structured_release_output_can_exceed_diagnostic_tail(capsys):
    payload = b"public-inventory\n" * 2000
    remaining = [payload]
    channel = SimpleNamespace(
        recv_ready=lambda: bool(remaining),
        recv=lambda _: remaining.pop(),
        recv_stderr_ready=lambda: False,
        exit_status_ready=lambda: not remaining,
        recv_exit_status=lambda: 0,
    )
    client = Mock()
    client.exec_command.return_value = (None, SimpleNamespace(channel=channel), None)
    assert (
        release_vps.run_remote(
            client, "inventory", "read-only", capture_limit=1_000_000, show_output=False
        )
        == payload.decode()
    )
    assert "public-inventory" not in capsys.readouterr().out


def test_large_gateway_inventory_keeps_every_digest(monkeypatch):
    rows = [f"{'a' * 64}  /srv/miniapp/assets/chunk-{i:08d}.js\n" for i in range(200)]
    remote = Mock(return_value="".join(rows))
    monkeypatch.setattr(release_vps, "run_remote", remote)
    inventory = release_vps.compatibility_chunks(Mock())
    assert len(inventory) == 200
    assert inventory["frontend/miniapp/dist/assets/chunk-00000000.js"] == "a" * 64
    assert remote.call_args.kwargs["capture_limit"] == 1_000_000
    assert remote.call_args.kwargs["show_output"] is False


def test_truncated_gateway_digest_is_rejected(monkeypatch):
    monkeypatch.setattr(
        release_vps,
        "run_remote",
        Mock(return_value="partial  /srv/miniapp/assets/chunk-00000000.js\n"),
    )
    with pytest.raises(RuntimeError, match="Incomplete gateway"):
        release_vps.compatibility_chunks(Mock())


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
