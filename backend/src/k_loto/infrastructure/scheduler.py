"""APScheduler adapter for periodic draw reconciliation."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from k_loto.application.scheduler import DrawRecoveryService
from k_loto.infrastructure.database.session import session_factory


class SchedulerRuntime:
    def __init__(self, interval_seconds: int) -> None:
        self._recovery = DrawRecoveryService(session_factory)
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._interval_seconds = interval_seconds

    async def start(self) -> None:
        await self._recovery.reconcile()
        self._scheduler.add_job(
            self._recovery.reconcile,
            trigger="interval",
            seconds=self._interval_seconds,
            id="draw-reconciliation",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
