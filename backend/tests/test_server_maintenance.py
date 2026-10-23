"""Isolated filesystem/Docker-plan regression tests; no production mutations."""

import gzip
import json
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
            self.directory, ARCHIVES, now=self.now, age_seconds=0, keep=keep
        )

    def test_only_latest_two_protected_even_when_all_archives_are_recent(
        self,
    ) -> None:
        for index in range(5):
            self.file(f"miniapp-before-1.0.0-{index}.tar.gz", index)
        self.file("before-branding-1.0.0-1.tar.gz", 40)
        self.file("miniapp-before-1.0.0-99.tar.gz", 1)
        names = {Path(item.path).name for item in self.candidates(2)}
        self.assertEqual(
            names, {f"miniapp-before-1.0.0-{i}.tar.gz" for i in (1, 2, 3, 4)}
        )

    def test_latest_two_are_shared_across_both_directories(self) -> None:
        second = self.directory / "second"
        second.mkdir()
        for index in range(6):
            item = self.file(f"miniapp-before-1.0.0-{index}.tar.gz", index)
            if index % 2:
                item.rename(second / item.name)
        protected_category = self.file("before-branding-1.0.0-1.tar.gz", 40)
        plan = select_files(
            self.directory,
            ARCHIVES,
            now=self.now,
            age_seconds=0,
            keep=2,
            extra_directories=(second, self.directory),
        )
        self.assertEqual(
            {Path(row.path).name for row in plan},
            {f"miniapp-before-1.0.0-{index}.tar.gz" for index in (2, 3, 4, 5)},
        )
        self.assertTrue(protected_category.exists())

    def test_count_only_policy_accepts_zero_age_but_not_negative_age(self) -> None:
        config = (
            Path(__file__).resolve().parents[2]
            / "infrastructure/server-maintenance.toml"
        )
        with patch.object(server_maintenance, "CONFIG", config):
            values = server_maintenance.policy()
        self.assertEqual(values["archive_min_age_days"], 0)
        self.assertEqual(values["archive_keep_per_category"], 2)
        self.assertEqual(values["database_backup_keep"], 2)
        self.assertEqual(values["image_keep_versions"], 3)
        invalid = self.directory / "invalid.toml"
        invalid.write_text(
            config.read_text().replace(
                "archive_min_age_days = 0", "archive_min_age_days = -1"
            )
        )
        with patch.object(server_maintenance, "CONFIG", invalid):
            with self.assertRaisesRegex(ValueError, "archive_min_age_days"):
                server_maintenance.policy()

    def test_policy_refuses_fewer_than_two_recovery_points(self) -> None:
        config = (
            Path(__file__).resolve().parents[2]
            / "infrastructure/server-maintenance.toml"
        )
        for key in ("database_backup_keep", "archive_keep_per_category"):
            with self.subTest(key=key):
                invalid = self.directory / (key + ".toml")
                invalid.write_text(
                    config.read_text().replace(f"{key} = 2", f"{key} = 1")
                )
                with patch.object(server_maintenance, "CONFIG", invalid):
                    with self.assertRaisesRegex(ValueError, key):
                        server_maintenance.policy()

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

    def test_legacy_project_label_and_feature_rollback_protection(self):
        images = [
            self.image(str(i), [f"k-loto-gateway:before-distribution-{i}"])
            for i in range(1, 5)
        ]
        legacy = self.image("legacy", [])
        legacy["Config"]["Labels"] = {"com.docker.compose.project": "k-loto"}
        images.append(legacy)
        plan = image_candidates(
            images, set(), now=self.now, keep=3, age_seconds=7 * 86400
        )
        self.assertEqual({row["Id"] for row in plan}, {"1", "2", "legacy"})

    def test_feature_release_families_share_last_three_without_age_protection(self):
        for index in range(5):
            self.file(f"distribution-followup-before-{index}.tar.gz", index)
        self.file("performance-before-99.tar.gz", 1)
        self.assertEqual(len(self.candidates(3)), 3)

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
            "archive_min_age_days": 0,
            "archive_keep_per_category": 3,
            "database_backup_keep": 7,
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
            patch.object(
                server_maintenance, "database_backup_candidates", return_value=[]
            ),
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

    def test_database_retention_keeps_two_recent_copies_and_ignores_partial_files(
        self,
    ):
        for index in range(9):
            self.file(f"k-loto-20261011T00000{index}Z.dump", index)
        self.file("k-loto-20261011T000009Z.dump.partial", 0)
        self.file("unrecognized.dump", 100)
        with (
            patch.object(server_maintenance, "DATABASE_BACKUPS", self.directory),
            patch.object(
                server_maintenance, "policy", return_value={"database_backup_keep": 2}
            ),
            patch.object(server_maintenance, "run", return_value=str(self.directory)),
        ):
            removed = server_maintenance.prune_database_backups()
        self.assertEqual(
            {Path(row).name for row in removed},
            {f"k-loto-20261011T00000{i}Z.dump" for i in range(2, 9)},
        )
        self.assertEqual(len(list(self.directory.glob("k-loto-*.dump"))), 2)
        self.assertTrue((self.directory / "unrecognized.dump").exists())
        self.assertTrue(
            (self.directory / "k-loto-20261011T000009Z.dump.partial").exists()
        )

    def test_invalid_retained_dump_stops_database_cleanup(self):
        for index in range(8):
            self.file(f"k-loto-20261011T00000{index}Z.dump", index)

        def inspect_or_fail(*arguments, **options):
            if "pg_restore" in arguments:
                raise subprocess.CalledProcessError(1, "pg_restore")
            return str(self.directory)

        with (
            patch.object(server_maintenance, "DATABASE_BACKUPS", self.directory),
            patch.object(
                server_maintenance, "policy", return_value={"database_backup_keep": 2}
            ),
            patch.object(server_maintenance, "run", side_effect=inspect_or_fail),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                server_maintenance.prune_database_backups()
        self.assertEqual(len(list(self.directory.glob("*.dump"))), 8)

    def test_database_cleanup_refuses_unexpected_volume(self):
        with patch.object(
            server_maintenance, "run", return_value="/unrelated/database"
        ):
            with self.assertRaisesRegex(
                RuntimeError, "Unexpected database backup volume"
            ):
                server_maintenance.database_backup_candidates(7)

    def test_second_retained_dump_failure_preserves_every_recovery_point(self):
        for index in range(5):
            self.file(f"k-loto-20261011T00000{index}Z.dump", index)
        inspected = []

        def inspect_or_fail(*arguments, **options):
            if "pg_restore" in arguments:
                inspected.append(arguments[-1])
                if len(inspected) == 2:
                    raise subprocess.CalledProcessError(1, "pg_restore")
            return str(self.directory)

        with (
            patch.object(server_maintenance, "DATABASE_BACKUPS", self.directory),
            patch.object(
                server_maintenance, "policy", return_value={"database_backup_keep": 2}
            ),
            patch.object(server_maintenance, "run", side_effect=inspect_or_fail),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                server_maintenance.prune_database_backups()
        self.assertEqual(len(inspected), 2)
        self.assertEqual(len(list(self.directory.glob("*.dump"))), 5)

    def test_zero_age_retention_also_counts_files_with_future_timestamps(self):
        for index in range(9):
            self.file(f"k-loto-20261011T00000{index}Z.dump", -index)
        plan = select_files(
            self.directory,
            server_maintenance.DATABASE_DUMPS,
            now=self.now,
            age_seconds=0,
            keep=7,
        )
        self.assertEqual(len(plan), 2)

    def test_new_images_expire_immediately_except_live_and_two_rollbacks(self):
        images = [
            self.image(str(i), [f"k-loto-api:before-release-{i}"]) for i in range(1, 5)
        ]
        for row in images:
            row["Created"] = "2099-01-01T00:00:00Z"
        self.assertEqual(
            {
                row["Id"]
                for row in image_candidates(
                    images, {"4"}, now=self.now, keep=3, age_seconds=0
                )
            },
            {"1"},
        )

    def test_changed_image_tags_or_new_container_reference_prevent_removal(self):
        planned = self.image("old", ["k-loto-api:before-release-1"])
        changed = self.image("old", ["k-loto-api:latest"])
        with patch.object(
            server_maintenance, "run", return_value=json.dumps([changed])
        ) as run:
            self.assertFalse(server_maintenance.remove_planned_image(planned, {"old"}))
            self.assertEqual(run.call_count, 1)
        with (
            patch.object(
                server_maintenance, "run", return_value=json.dumps([planned])
            ) as run,
            patch.object(server_maintenance, "referenced_images", return_value={"old"}),
        ):
            self.assertFalse(server_maintenance.remove_planned_image(planned, {"old"}))
            self.assertEqual(run.call_count, 1)

    def test_cache_prune_uses_512_mb_without_age_filter(self):
        with patch.object(server_maintenance, "run") as run:
            server_maintenance.prune_build_cache(512, 0)
        run.assert_called_once_with(
            "docker",
            "builder",
            "prune",
            "--all",
            "--force",
            "--keep-storage",
            "512MB",
            timeout=300,
        )

    def test_required_intermediate_parent_is_preserved_without_force(self):
        planned = self.image("parent", [])
        planned["Config"]["Labels"] = {"com.docker.compose.project": "k-loto"}
        failure = subprocess.CalledProcessError(
            1, "docker image rm", stderr="conflict: image has dependent child images"
        )
        with (
            patch.object(
                server_maintenance, "run", side_effect=[json.dumps([planned]), failure]
            ) as run,
            patch.object(server_maintenance, "referenced_images", return_value=set()),
        ):
            self.assertFalse(
                server_maintenance.remove_planned_image(planned, {"parent"})
            )
        self.assertNotIn("--force", run.call_args.args)

    def test_parent_already_removed_by_docker_does_not_abort_cleanup(self):
        planned = self.image("parent", [])
        failure = subprocess.CalledProcessError(
            1, "docker image inspect", stderr="Error: No such image: parent"
        )
        with patch.object(server_maintenance, "run", side_effect=failure) as run:
            self.assertFalse(
                server_maintenance.remove_planned_image(planned, {"parent"})
            )
        self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
