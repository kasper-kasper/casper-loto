"""Bounded operational samples without request bodies, identities or credentials."""

import asyncio
import json
import math
import re
import shutil
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic
from typing import Any

import structlog
from sqlalchemy import func, select

from k_loto.application.achievement_release import queue_health
from k_loto.application.publication_monitoring import delayed_publications
from k_loto.domain.enums import DrawStatus
from k_loto.infrastructure.database.models import (
    DistributionAnnouncement,
    Draw,
    SchedulerHeartbeat,
)
from k_loto.infrastructure.database.session import session_factory

logger = structlog.get_logger(__name__)
METRICS = {
    "dashboard",
    "purchase",
    "account",
    "miniapp",
    "startup_client",
    "dashboard_client",
    "purchase_client",
}


def backup_state(directory: Path) -> tuple[int, float | None]:
    stamps: list[float] = []
    for item in directory.glob("k-loto-*.dump"):
        if not re.fullmatch(r"k-loto-\d{8}T\d{6}Z\.dump", item.name):
            continue
        try:
            if item.is_file() and item.stat().st_size > 0:
                stamps.append(item.stat().st_mtime)
        except FileNotFoundError:
            # Retention may remove a previous dump during the scan.
            continue
    return len(stamps), max(stamps, default=None)


def host_state() -> dict[str, Any] | None:
    try:
        raw = Path("/host-monitor/state.json").read_text(encoding="utf-8")
        value: dict[str, Any] = json.loads(raw)
        return value
    except (OSError, ValueError):
        return None


class RuntimeMonitoring:
    def __init__(self) -> None:
        self.samples: dict[str, deque[tuple[float, float, int]]] = {
            name: deque(maxlen=10_000) for name in METRICS
        }
        self.operations: dict[str, Any] = {
            "checked_at": None,
            "warnings": ["monitor_warming_up"],
        }

    def record(self, metric: str, duration_ms: float, status: int) -> None:
        if metric not in METRICS or not math.isfinite(duration_ms):
            return
        self.samples[metric].append(
            (monotonic(), max(0, min(duration_ms, 120_000)), status)
        )

    def snapshot(self) -> dict[str, Any]:
        cutoff = monotonic() - 3600
        summary: dict[str, Any] = {}
        for name, samples in self.samples.items():
            while samples and samples[0][0] < cutoff:
                samples.popleft()
            durations = sorted(item[1] for item in samples)
            summary[name] = {
                "count": len(samples),
                "errors": sum(item[2] == 0 or item[2] >= 500 for item in samples),
                "p50_ms": round(durations[(len(durations) - 1) // 2])
                if durations
                else None,
                "p95_ms": round(durations[math.ceil(len(durations) * 0.95) - 1])
                if durations
                else None,
            }
        warnings = list(self.operations.get("warnings", []))
        for metric, limit in (
            ("startup_client", 4000),
            ("purchase_client", 2000),
            ("purchase", 1000),
        ):
            data = summary[metric]
            if data["count"] >= 5 and (data["p95_ms"] or 0) > limit:
                warnings.append(f"slow_{metric}")
        for metric in ("miniapp", "purchase_client"):
            data = summary[metric]
            if data["count"] >= 10 and data["errors"] / data["count"] >= 0.05:
                warnings.append(f"errors_{metric}")
        checked = self.operations.get("checked_at")
        if checked and datetime.now(UTC) - datetime.fromisoformat(checked) > timedelta(
            minutes=3
        ):
            warnings.append("monitor_stale")
        return {
            "window_seconds": 3600,
            "max_samples_per_metric": 10_000,
            "metrics": summary,
            "operations": {**self.operations, "warnings": warnings},
        }

    async def inspect(self, backup_dir: Path, stuck_minutes: int) -> None:
        now = datetime.now(UTC)
        cutoff = now - timedelta(minutes=stuck_minutes)
        warnings: list[str] = []
        host = await asyncio.to_thread(host_state)
        if host is None or now - datetime.fromisoformat(host["checked_at"]) > timedelta(
            minutes=3
        ):
            warnings.append("host_monitor_stale")
        elif host["warnings"]:
            warnings.append("host_monitor_warning")
        disk = shutil.disk_usage("/")
        used_percent = round((disk.total - disk.free) / disk.total * 100, 1)
        if used_percent >= 80:
            warnings.append("disk_low")
        dump_count, newest = await asyncio.to_thread(backup_state, backup_dir)
        age = max(0, int(now.timestamp() - newest)) if newest else None
        if age is None or age > 26 * 3600:
            warnings.append("backup_missing_or_stale")
        if dump_count > 7:
            warnings.append("backup_retention_exceeded")
        async with session_factory() as session:
            overdue = int(
                await session.scalar(
                    select(func.count(Draw.id)).where(
                        Draw.status.not_in(
                            (DrawStatus.COMPLETED, DrawStatus.CANCELLED)
                        ),
                        Draw.scheduled_at < cutoff,
                    )
                )
                or 0
            )
            delayed_distribution = int(
                await session.scalar(
                    select(func.count(DistributionAnnouncement.id)).where(
                        DistributionAnnouncement.state.in_(
                            ["queued", "sending", "failed", "uncertain"]
                        ),
                        DistributionAnnouncement.created_at < cutoff,
                    )
                )
                or 0
            )
            delayed_posts = await delayed_publications(
                session, now=now, grace=timedelta(minutes=stuck_minutes)
            )
            heartbeat = await session.get(SchedulerHeartbeat, 1)
            last_success = heartbeat.last_succeeded_at if heartbeat else None
            achievements = await queue_health(session, now)
        if achievements.get("activation_overdue"):
            warnings.append("achievement_activation_overdue")
        if achievements.get("blocked"):
            warnings.append("achievement_events_blocked")
        if (
            achievements.get("enabled")
            and not achievements.get("processing_paused")
            and achievements.get("lag_seconds", 0) > 300
        ):
            warnings.append("achievement_queue_delayed")
        if overdue:
            warnings.append("overdue_draws")
        if delayed_distribution or delayed_posts:
            warnings.append("delayed_publications")
        if last_success is None or last_success < cutoff:
            warnings.append("scheduler_stale")
        self.operations = {
            "checked_at": now.isoformat(),
            "warnings": warnings,
            "disk_used_percent": used_percent,
            "disk_free_bytes": disk.free,
            "backup_count": dump_count,
            "backup_age_seconds": age,
            "overdue_draws": overdue,
            "delayed_distribution_posts": delayed_distribution,
            "delayed_posts": delayed_posts,
            "host_monitor": host,
            "achievements": achievements,
        }

    async def run(self, backup_dir: Path, stuck_minutes: int) -> None:
        while True:
            try:
                async with asyncio.timeout(15):
                    await self.inspect(backup_dir, stuck_minutes)
                snapshot = self.snapshot()
                logger.info("operational_snapshot", **snapshot)
            except Exception as error:
                # Error messages can contain DSNs/tokens. Keep only their type.
                self.operations = {
                    **self.operations,
                    "warnings": ["monitor_check_failed"],
                }
                logger.error(
                    "operational_check_failed", error_type=type(error).__name__
                )
            await asyncio.sleep(60)


runtime_monitoring = RuntimeMonitoring()
