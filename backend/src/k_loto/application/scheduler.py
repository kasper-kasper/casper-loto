"""Draw preparation and chronological missed-draw recovery."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.application.weekly import WeeklySettlementService
from k_loto.domain.enums import DrawStatus, LotteryKind
from k_loto.domain.schedules import next_draw_at, sales_close_at
from k_loto.infrastructure.database.models import Draw, Lottery

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    settled_draw_ids: tuple[UUID, ...]
    prepared_draw_ids: tuple[UUID, ...]


class DrawScheduleService:
    """Prepare exactly one draw still open for sales under a lottery row lock."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_next_draw(
        self, lottery_id: UUID, *, reference: datetime
    ) -> tuple[Draw, bool]:
        async with self._session.begin():
            lottery = await self._session.scalar(
                select(Lottery).where(Lottery.id == lottery_id).with_for_update()
            )
            if lottery is None:
                raise LookupError("Lottery does not exist.")

            pending = await self._session.scalar(
                select(Draw)
                .where(
                    Draw.lottery_id == lottery.id,
                    Draw.status != DrawStatus.COMPLETED,
                    Draw.sales_close_at > reference,
                )
                .order_by(Draw.scheduled_at)
                .limit(1)
            )
            if pending is not None:
                return pending, False

            latest = await self._session.scalar(
                select(Draw)
                .where(Draw.lottery_id == lottery.id)
                .order_by(Draw.scheduled_at.desc())
                .limit(1)
            )
            schedule_base = latest.scheduled_at if latest is not None else reference
            scheduled_at = next_draw_at(lottery.kind, schedule_base)
            draw = Draw(
                id=uuid4(),
                lottery_id=lottery.id,
                public_number=lottery.next_draw_number,
                status=DrawStatus.SCHEDULED,
                scheduled_at=scheduled_at,
                sales_close_at=sales_close_at(lottery.kind, scheduled_at),
                correlation_id=uuid4(),
                ticket_count=0,
                total_sales=0,
                total_payout=0,
                reserve_used=0,
            )
            lottery.next_draw_number += 1
            self._session.add(draw)
        return draw, True


class DrawRecoveryService:
    """Reconcile prepared and missed Weekly draws after startup or on interval."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def _active_lottery_ids(self) -> list[UUID]:
        async with self._session_factory() as session:
            return list(
                (
                    await session.scalars(
                        select(Lottery.id)
                        .where(Lottery.is_active.is_(True))
                        .order_by(Lottery.code)
                    )
                ).all()
            )

    async def _next_due_weekly(self, now: datetime) -> UUID | None:
        async with self._session_factory() as session:
            draw_id = await session.scalar(
                select(Draw.id)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .where(
                    Lottery.kind == LotteryKind.WEEKLY,
                    Draw.status != DrawStatus.COMPLETED,
                    Draw.scheduled_at <= now,
                )
                .order_by(Draw.scheduled_at, Draw.public_number)
                .limit(1)
            )
        return draw_id

    async def _lottery_id_for_draw(self, draw_id: UUID) -> UUID:
        async with self._session_factory() as session:
            lottery_id = await session.scalar(
                select(Draw.lottery_id).where(Draw.id == draw_id)
            )
        if lottery_id is None:
            raise LookupError("Settled draw disappeared from business history.")
        return lottery_id

    async def reconcile(self, *, now: datetime | None = None) -> RecoveryReport:
        timestamp = now or datetime.now(UTC)
        prepared: list[UUID] = []
        settled: list[UUID] = []

        for lottery_id in await self._active_lottery_ids():
            async with self._session_factory() as session:
                draw, created = await DrawScheduleService(session).ensure_next_draw(
                    lottery_id, reference=timestamp
                )
                if created:
                    prepared.append(draw.id)

        while due_draw_id := await self._next_due_weekly(timestamp):
            async with self._session_factory() as session:
                result = await WeeklySettlementService(session).settle(
                    due_draw_id, now=timestamp
                )
            if not result.already_completed:
                settled.append(due_draw_id)

            lottery_id = await self._lottery_id_for_draw(due_draw_id)
            async with self._session_factory() as session:
                draw, created = await DrawScheduleService(session).ensure_next_draw(
                    lottery_id, reference=timestamp
                )
                if created:
                    prepared.append(draw.id)

        report = RecoveryReport(tuple(settled), tuple(prepared))
        logger.info(
            "draw_reconciliation_complete",
            settled_count=len(report.settled_draw_ids),
            prepared_count=len(report.prepared_draw_ids),
        )
        return report
