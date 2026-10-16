"""APScheduler adapter for periodic draw reconciliation."""

from datetime import UTC, datetime, timedelta

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.dialects.postgresql import insert

from k_loto.application.auto_play import AutoPlayService
from k_loto.application.engagement import PlayerEngagementService
from k_loto.application.operational_monitoring import OperationalMonitoringService
from k_loto.application.publication_automation import PublicationAutomation, drain
from k_loto.application.scheduler import DrawRecoveryService
from k_loto.core.config import get_settings
from k_loto.infrastructure.database.models import SchedulerHeartbeat
from k_loto.infrastructure.database.session import session_factory

logger = structlog.get_logger(__name__)


class PartialDrawRecoveryError(RuntimeError):
    """Some lotteries remain blocked; the heartbeat must not report success."""


class SchedulerRuntime:
    def __init__(self, interval_seconds: int) -> None:
        settings = get_settings()
        self._recovery = DrawRecoveryService(session_factory)
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._interval_seconds = interval_seconds
        self._monitor = OperationalMonitoringService(
            session_factory,
            owner_telegram_id=settings.owner_telegram_id,
            stuck_after=timedelta(minutes=settings.operational_stuck_minutes),
        )

    async def start(self) -> None:
        try:
            await self._run()
        except Exception as error:
            # Keep the API/admin available and install the periodic recovery retry.
            logger.error(
                "scheduler_startup_recovery_failed", error_type=type(error).__name__
            )
        await self._run_publication_events()
        self._scheduler.add_job(
            self._run_publication_events,
            trigger="interval",
            seconds=self._interval_seconds,
            id="publication-event-reconciliation",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self._scheduler.add_job(
            self._run_publication_delivery,
            trigger="interval",
            seconds=2,
            id="publication-delivery",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self._scheduler.add_job(
            self._run,
            trigger="interval",
            seconds=self._interval_seconds,
            id="draw-reconciliation",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self._scheduler.start()

    async def _run_publication_events(self) -> None:
        try:
            async with session_factory() as session:
                from k_loto.application.publication_events import due_slot, event_config
                from k_loto.infrastructure.database.models import PublicationEventState

                state = await session.get(
                    PublicationEventState, "publication.transport"
                )
                progress = await session.get(
                    PublicationEventState, "publication.automation"
                )
                enabled = bool(state and state.value.get("enabled"))
                start = progress.value.get("collected_until") if progress else None
            now = datetime.now(UTC)
            if (
                enabled
                and start
                and due_slot(now, event_config())
                > due_slot(datetime.fromisoformat(start), event_config())
            ):
                async with session_factory() as session:
                    await PublicationAutomation(session).collect(
                        datetime.fromisoformat(start), now, historical=False
                    )
        except Exception:
            # Editorial failures must never prevent money/draw recovery.
            logger.exception("publication_event_scan_failed")

    async def _run_publication_delivery(self) -> None:
        try:
            from k_loto.application.publication_retention import expire_proposals

            await expire_proposals(session_factory, now=datetime.now(UTC))
        except Exception as error:
            logger.error("proposal_expiration_failed", error_type=type(error).__name__)
        try:
            from k_loto.application.distribution import drain_distribution

            await drain_distribution(session_factory)
        except Exception as error:
            # No exception text: HTTP errors can embed bot credentials.
            logger.error("publication_delivery_failed", error_type=type(error).__name__)
        try:
            await drain(session_factory)
        except Exception as error:
            logger.error("editorial_delivery_failed", error_type=type(error).__name__)

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
            async with session_factory() as session, session.begin():
                heartbeat = await session.get(SchedulerHeartbeat, 1)
                if heartbeat is not None:
                    heartbeat.settled_count = len(report.settled_draw_ids)
                    heartbeat.prepared_count = len(report.prepared_draw_ids)
            if report.failed_lottery_ids:
                raise PartialDrawRecoveryError()
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
