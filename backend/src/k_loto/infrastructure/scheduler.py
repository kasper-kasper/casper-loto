"""APScheduler adapter for periodic draw reconciliation."""

from datetime import UTC, datetime, timedelta

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.dialects.postgresql import insert

from k_loto.application.auto_play import AutoPlayService
from k_loto.application.engagement import PlayerEngagementService
from k_loto.application.interesting_facts import InterestingFactService
from k_loto.application.operational_monitoring import OperationalMonitoringService
from k_loto.application.scheduler import DrawRecoveryService
from k_loto.core.config import get_settings
from k_loto.infrastructure.database.models import SchedulerHeartbeat
from k_loto.infrastructure.database.session import session_factory

logger = structlog.get_logger(__name__)


class SchedulerRuntime:
    def __init__(self, interval_seconds: int) -> None:
        settings = get_settings()
        self._recovery = DrawRecoveryService(session_factory)
        self._interesting_facts = InterestingFactService(session_factory)
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._interval_seconds = interval_seconds
        self._monitor = OperationalMonitoringService(
            session_factory,
            owner_telegram_id=settings.owner_telegram_id,
            stuck_after=timedelta(minutes=settings.operational_stuck_minutes),
        )

    async def start(self) -> None:
        await self._run()
        await self._run_interesting_facts()
        self._scheduler.add_job(
            self._run,
            trigger="interval",
            seconds=self._interval_seconds,
            id="draw-reconciliation",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self._scheduler.add_job(
            self._run_interesting_facts,
            trigger=CronTrigger(
                hour=4,
                minute=10,
                timezone="Europe/Moscow",
            ),
            id="daily-interesting-facts",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self._scheduler.start()

    async def _run_interesting_facts(self) -> None:
        try:
            generated = await self._interesting_facts.run_if_due(now=datetime.now(UTC))
            if generated:
                logger.info("interesting_facts_generated")
        except Exception:
            # Content suggestions must never stop settlement or draw recovery.
            logger.exception("interesting_facts_generation_failed")

    async def _run(self) -> None:
        started = datetime.now(UTC)
        async with session_factory() as session, session.begin():
            await session.execute(
                insert(SchedulerHeartbeat)
                .values(id=1, last_started_at=started)
                .on_conflict_do_update(
                    index_elements=[SchedulerHeartbeat.id],
                    set_={"last_started_at": started},
                )
            )
        try:
            report = await self._recovery.reconcile(now=started)
            await AutoPlayService(session_factory).run(now=started)
            await PlayerEngagementService(session_factory).run(now=started)
        except Exception as error:
            async with session_factory() as session, session.begin():
                heartbeat = await session.get(SchedulerHeartbeat, 1)
                if heartbeat is not None:
                    heartbeat.last_failed_at = datetime.now(UTC)
                    heartbeat.last_error = type(error).__name__[:256]
            try:
                await self._monitor.alert_scheduler_error(
                    type(error).__name__, now=started
                )
            except Exception:
                logger.exception("scheduler_owner_alert_failed")
            raise
        try:
            await self._monitor.run(now=started)
        except Exception:
            logger.exception("operational_monitor_failed")
        async with session_factory() as session, session.begin():
            heartbeat = await session.get(SchedulerHeartbeat, 1)
            if heartbeat is not None:
                heartbeat.last_succeeded_at = datetime.now(UTC)
                heartbeat.last_error = None
                heartbeat.settled_count = len(report.settled_draw_ids)
                heartbeat.prepared_count = len(report.prepared_draw_ids)

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
