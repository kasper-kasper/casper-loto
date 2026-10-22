"""Scoped content cleanup requires an off-host copy and quiescent writers."""

import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from scripts import server_maintenance as maintenance


def test_cleanup_requires_owner_receipt_before_any_command(monkeypatch):
    run = Mock()
    monkeypatch.setattr(maintenance, "run", run)
    with pytest.raises(RuntimeError, match="authorization"):
        maintenance.retire_editorial_data({"local_archive_verified": True})
    with pytest.raises(RuntimeError, match="verified"):
        maintenance.retire_editorial_data(
            {
                "authorization": "channel-and-stories-removal-2026-10-19",
            }
        )
    run.assert_not_called()


def test_cleanup_refuses_running_business_writers(monkeypatch):
    monkeypatch.setattr(maintenance, "run", lambda *_: "true")
    with pytest.raises(RuntimeError, match="Quiesce"):
        maintenance.retire_editorial_data(
            {
                "authorization": "channel-and-stories-removal-2026-10-19",
                "local_archive_verified": True,
            }
        )


def test_archived_content_only_deleted_if_exact_copy_matches(tmp_path, monkeypatch):
    monkeypatch.setattr(maintenance, "ROOT", tmp_path.resolve())
    image = tmp_path / "assets/publications/example.webp"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"archived bytes")
    with pytest.raises(RuntimeError, match="changed"):
        maintenance.delete_archived_editorial_file(image, "0" * 64)
    assert image.exists()
    assert maintenance.delete_archived_editorial_file(
        image, hashlib.sha256(b"archived bytes").hexdigest()
    )
    assert not image.exists()


@pytest.mark.parametrize(
    "name", [".env.production", "backend/ledger.py", "../other.webp"]
)
def test_unrelated_paths_never_deleted(tmp_path, monkeypatch, name):
    monkeypatch.setattr(maintenance, "ROOT", tmp_path.resolve())
    with pytest.raises(RuntimeError, match="scope"):
        maintenance.delete_archived_editorial_file(tmp_path / name, "0" * 64)


def test_editorial_sql_does_not_disable_ledger_or_draw_guards():
    sql = maintenance.EDITORIAL_RETIREMENT_SQL
    assert "WHERE entity_type = 'PUBLICATION'" in sql
    assert "ENABLE TRIGGER trg_admin_audit_immutable" in sql
    assert "CASCADE" not in sql and "session_replication_role" not in sql
    assert "DELETE FROM tickets" not in sql and "DELETE FROM draws" not in sql
    assert "DELETE FROM ledger" not in sql


@pytest.mark.parametrize("used", [False, True])
def test_image_cleanup_preserves_new_runtime_and_unrelated_base(monkeypatch, used):
    old, content, base, current = ["sha256:" + char * 64 for char in "abcd"]
    images = [
        {"Id": old, "Parent": content, "RepoTags": ["k-loto-api:before-release-1"]},
        {"Id": content, "Parent": base, "RepoTags": []},
        {"Id": base, "Parent": "", "RepoTags": ["python:3.12-slim"]},
        {"Id": current, "Parent": base, "RepoTags": ["k-loto-api:latest"]},
    ]
    history = [
        {"ID": old, "CreatedBy": "CMD python"},
        {"ID": content, "CreatedBy": "COPY images /app/publication-assets"},
        {"ID": base, "CreatedBy": "FROM python"},
    ]
    deleted = []

    def run(*args):
        if args[:3] == ("docker", "image", "history"):
            return "\n".join(json.dumps(row) for row in history)
        if args[:3] == ("docker", "image", "ls"):
            return "\n".join(row["Id"] for row in images)
        if args[:3] == ("docker", "image", "inspect"):
            return json.dumps(images)
        if args[:2] == ("docker", "ps"):
            return "still-used" if used else ""
        if args[:3] == ("docker", "image", "rm"):
            deleted.extend(args[3:])
            return ""
        raise AssertionError(args)

    def inspect(args, **_kwargs):
        matches = [row for row in images if row["Id"] == args[-1]]
        return SimpleNamespace(returncode=0, stdout=json.dumps(matches))

    monkeypatch.setattr(maintenance, "run", run)
    monkeypatch.setattr(maintenance.subprocess, "run", inspect)
    receipt = {"local_archive_verified": True, "archived_images": [{"id": old}]}
    if used:
        with pytest.raises(RuntimeError, match="still used"):
            maintenance.retire_archived_editorial_images(receipt)
        assert deleted == []
    else:
        assert maintenance.retire_archived_editorial_images(receipt) == {
            "retired_editorial_image_records": 2
        }
        assert deleted == ["k-loto-api:before-release-1", content]


def test_editorial_cache_cleanup_always_has_an_exact_id_filter(monkeypatch):
    run = Mock()
    monkeypatch.setattr(maintenance, "run", run)
    receipt = {"local_archive_verified": True, "archived_build_cache_ids": ["a" * 25]}
    maintenance.prune_archived_editorial_cache(receipt)
    assert run.call_args.args == (
        "docker",
        "builder",
        "prune",
        "--all",
        "--force",
        "--filter",
        "id=" + "a" * 25,
    )
    run.reset_mock()
    maintenance.prune_archived_editorial_cache({"local_archive_verified": True})
    run.assert_not_called()
    with pytest.raises(RuntimeError, match="Invalid"):
        maintenance.prune_archived_editorial_cache(
            {
                "local_archive_verified": True,
                "archived_build_cache_ids": ["*"],
            }
        )
