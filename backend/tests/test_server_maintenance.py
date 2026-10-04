"""Isolated filesystem/Docker-plan regression tests; no production mutations."""

import gzip
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import server_maintenance
from scripts.server_maintenance import (
    ARCHIVES,
    DIAGNOSTIC_LOGS,
    UPLOADS,
    active_operation,
    archive_diagnostic_logs,
    delete_planned_file,
    image_candidates,
    select_files,
)


class MaintenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.now = time.time()

    def file(self, name: str, days: int = 20) -> Path:
        item = self.directory / name
        item.write_text("disposable fixture")
        timestamp = self.now - days * 86400
        os.utime(item, (timestamp, timestamp))
        return item

    def candidates(self, keep: int = 0):
        return select_files(
            self.directory, ARCHIVES, now=self.now, age_seconds=14 * 86400, keep=keep
        )

    def test_age_and_count_both_protect_archives_per_category(self) -> None:
        for index in range(5):
            self.file(f"miniapp-before-1.0.0-{index}.tar.gz", 20 + index)
        self.file("before-branding-1.0.0-1.tar.gz", 40)
        self.file("miniapp-before-1.0.0-99.tar.gz", 1)
        names = {Path(item.path).name for item in self.candidates(3)}
        self.assertEqual(names, {f"miniapp-before-1.0.0-{i}.tar.gz" for i in (2, 3, 4)})

    def test_never_selects_dump_unknown_directory_or_hardlink(self) -> None:
        self.file("k-loto-20260101.dump", 50)
        self.file("personal.tar.gz", 50)
        (self.directory / "miniapp-before-1.0.0-1.tar.gz").mkdir()
        source = self.file("original.txt", 50)
        os.link(source, self.directory / "miniapp-before-1.0.0-2.tar.gz")
        self.assertEqual(self.candidates(), [])

    def test_temp_upload_allowlist_excludes_unrelated_projects(self) -> None:
        self.file("miniapp-1.0.0-1.tar.gz", 3)
        self.file("other-project.tar.gz", 30)
        self.file("branding-1.0.0-2.tar.gz", 1)
        plan = select_files(
            self.directory, UPLOADS, now=self.now, age_seconds=48 * 3600, keep=0
        )
        self.assertEqual(
            [Path(row.path).name for row in plan], ["miniapp-1.0.0-1.tar.gz"]
        )

    def test_replaced_file_is_not_deleted(self) -> None:
        item = self.file("miniapp-before-1.0.0-1.tar.gz")
        (planned,) = self.candidates()
        item.write_text("new publication with different content")
        self.assertFalse(delete_planned_file(planned))
        self.assertTrue(item.exists())

    def test_valid_planned_file_is_removed_without_removing_other_files(self) -> None:
        item = self.file("miniapp-before-1.0.0-1.tar.gz")
        other = self.file("important.dump")
        (planned,) = self.candidates()
        self.assertTrue(delete_planned_file(planned))
        self.assertFalse(item.exists())
        self.assertTrue(other.exists())

    def test_symlink_is_not_selected_or_followed(self) -> None:
        item = self.file("miniapp-before-1.0.0-1.tar.gz")
        (planned,) = self.candidates()
        target = self.file("important.dump")
        item.unlink()
        try:
            item.symlink_to(target)
        except OSError:
            self.skipTest("Host cannot create symlinks; Linux test required")
        self.assertEqual(self.candidates(), [])
        self.assertFalse(delete_planned_file(planned))
        self.assertTrue(target.exists())

    def test_preserves_running_latest_and_two_rollback_versions(self) -> None:
        images = [
            self.image(str(i), [f"k-loto-gateway:before-miniapp-{i}"])
            for i in range(1, 6)
        ]
        images.append(self.image("live", ["k-loto-gateway:latest"]))
        plan = image_candidates(
            images, {"live", "1"}, now=self.now, keep=3, age_seconds=7 * 86400
        )
        self.assertEqual({row["Id"] for row in plan}, {"2", "3"})

    def test_does_not_delete_cross_project_tags_or_unknown_images(self) -> None:
        images = [
            self.image("shared", ["k-loto-gateway:old", "other:old"]),
            self.image("unknown", []),
            self.image("other", ["other:old"]),
        ]
        self.assertEqual(
            image_candidates(
                images, set(), now=self.now, keep=3, age_seconds=7 * 86400
            ),
            [],
        )

    def test_busy_operation_detection_excludes_own_read_only_commands(self) -> None:
        self.assertTrue(
            active_operation(["/usr/bin/docker", "compose", "build", "bot"])
        )
        self.assertTrue(active_operation(["pg_dump", "-Fc"]))
        self.assertTrue(
            active_operation(["tar", "-xzf", "/tmp/miniapp-1.0.0-1.tar.gz"])
        )
        self.assertFalse(active_operation(["docker", "image", "inspect", "id"]))
        self.assertFalse(active_operation(["python3", "scripts/server_maintenance.py"]))

    def image(self, identifier: str, tags: list[str]) -> dict:
        return {
            "Id": identifier,
            "RepoTags": tags,
            "Created": "2026-01-01T00:00:00Z",
            "Config": {"Labels": {}},
        }

    def test_important_logs_have_independent_90_day_retention(self) -> None:
        self.file("api-20260101T000000000000Z-aaaaaaaaaaaa.log.gz", 91)
        self.file("bot-20260102T000000000000Z-bbbbbbbbbbbb.log.gz", 89)
        self.file("financial-ledger.dump", 200)
        plan = select_files(
            self.directory,
            DIAGNOSTIC_LOGS,
            now=self.now,
            age_seconds=90 * 86400,
            keep=0,
        )
        self.assertEqual(len(plan), 1)
        self.assertTrue(Path(plan[0].path).name.startswith("api-"))

    def test_capture_compresses_logs_and_uses_cursor_only_for_same_container(self):
        commands = []

        def logs(command, **options):
            commands.append(command)
            options["stdout"].write(b"fixture draw/balance diagnostic\n")
            return subprocess.CompletedProcess(command, 0)

        with (
            patch.object(server_maintenance, "ROOT", self.directory),
            patch.object(server_maintenance, "run", return_value="a" * 64),
            patch.object(server_maintenance.subprocess, "run", side_effect=logs),
        ):
            archive_diagnostic_logs()
            archive_diagnostic_logs()
            self.assertNotIn("--since", commands[0])
            self.assertIn("--since", commands[2])
            with patch.object(server_maintenance, "run", return_value="b" * 64):
                archive_diagnostic_logs()
            self.assertNotIn("--since", commands[4])
        archives = list((self.directory / ".maintenance/diagnostic-logs").glob("*.gz"))
        self.assertTrue(archives)
        for archive in archives:
            with gzip.open(archive) as saved:
                self.assertEqual(saved.read(), b"fixture draw/balance diagnostic\n")

    def test_failed_capture_does_not_advance_cursor_or_publish_failed_logs(self):
        def failed(command, **options):
            options["stdout"].write(b"fixture private diagnostic error")
            return subprocess.CompletedProcess(command, 1)

        with (
            patch.object(server_maintenance, "ROOT", self.directory),
            patch.object(server_maintenance, "run", return_value="a" * 64),
            patch.object(server_maintenance.subprocess, "run", side_effect=failed),
        ):
            with self.assertRaisesRegex(RuntimeError, "capture failed: api"):
                archive_diagnostic_logs()
        self.assertFalse((self.directory / ".maintenance/log-cursors.json").exists())
        self.assertEqual(
            list((self.directory / ".maintenance/diagnostic-logs").iterdir()), []
        )

    def test_capture_failure_stops_cleanup_before_deletion(self):
        values = {
            "publication_grace_minutes": 15,
            "archive_min_age_days": 14,
            "archive_keep_per_category": 3,
            "upload_min_age_hours": 48,
            "diagnostic_log_retention_days": 90,
            "image_keep_versions": 3,
            "image_min_age_days": 7,
            "cache_keep_mb": 512,
            "cache_min_age_hours": 48,
        }
        with (
            patch.object(server_maintenance, "ROOT", self.directory),
            patch.object(server_maintenance, "policy", return_value=values),
            patch.object(server_maintenance, "check_health"),
            patch.object(server_maintenance, "busy_host", return_value=False),
            patch.object(server_maintenance, "select_files", return_value=[]),
            patch.object(server_maintenance, "inspect_images", return_value=[]),
            patch.object(server_maintenance, "referenced_images", return_value=set()),
            patch.object(
                server_maintenance,
                "archive_diagnostic_logs",
                side_effect=RuntimeError("capture unavailable"),
            ),
            patch.object(server_maintenance, "delete_planned_file") as delete,
            patch.object(server_maintenance, "run") as docker,
        ):
            with self.assertRaisesRegex(RuntimeError, "capture unavailable"):
                server_maintenance.maintain(apply=True)
            delete.assert_not_called()
            docker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
