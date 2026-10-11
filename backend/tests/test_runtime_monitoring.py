"""Bounded, redacted operational monitoring and backup freshness inputs."""

from time import monotonic

from k_loto.application.runtime_monitoring import RuntimeMonitoring, backup_state


def test_metrics_are_bounded_expire_and_reject_arbitrary_labels() -> None:
    monitor = RuntimeMonitoring()
    for _ in range(10_010):
        monitor.record("purchase", 100, 201)
    monitor.record("user-secret", 100, 500)
    monitor.record("purchase", float("nan"), 500)
    assert len(monitor.samples["purchase"]) == 10_000
    assert "user-secret" not in monitor.samples
    monitor.samples["account"].append((monotonic() - 3601, 300, 500))
    assert monitor.snapshot()["metrics"]["account"]["count"] == 0


def test_slow_purchase_and_network_errors_raise_warnings() -> None:
    monitor = RuntimeMonitoring()
    monitor.operations = {"checked_at": None, "warnings": []}
    for _ in range(10):
        monitor.record("purchase_client", 2500, 0)
    snapshot = monitor.snapshot()
    assert snapshot["metrics"]["purchase_client"]["p95_ms"] == 2500
    assert "slow_purchase_client" in snapshot["operations"]["warnings"]
    assert "errors_purchase_client" in snapshot["operations"]["warnings"]


def test_backups_ignore_partial_unrecognized_and_empty_files(tmp_path) -> None:
    (tmp_path / "k-loto-20261011T030000Z.dump").write_bytes(b"validated dump")
    (tmp_path / "k-loto-20261011T040000Z.dump.partial").write_bytes(b"unfinished")
    (tmp_path / "k-loto-20261011T050000Z.dump").write_bytes(b"")
    (tmp_path / "random.dump").write_bytes(b"other")
    count, newest = backup_state(tmp_path)
    assert count == 1
    assert newest is not None
