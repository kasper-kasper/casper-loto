"""APScheduler adapter for periodic draw reconciliation."""

from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.dialects.postgresql import insert

from k_loto.application.scheduler import DrawRecoveryService
from k_loto.infrastructure.database.models import SchedulerHeartbeat
from k_loto.infrastructure.database.session import session_factory


class SchedulerRuntime:
    def __init__(self, interval_seconds: int) -> None:
        self._recovery = DrawRecoveryService(session_factory)
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._interval_seconds = interval_seconds

    async def start(self) -> None:
        await self._run()
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
        except Exception as error:
            async with session_factory() as session, session.begin():
                heartbeat = await session.get(SchedulerHeartbeat, 1)
                if heartbeat is not None:
                    heartbeat.last_failed_at = datetime.now(UTC)
                    heartbeat.last_error = type(error).__name__[:256]
            raise
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
