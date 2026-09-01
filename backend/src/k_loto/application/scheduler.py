"""Draw preparation and chronological missed-draw recovery."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.application.daily_transition import DailyTransitionService
from k_loto.application.weekly import (
    LotterySettlementService,
    draw_configuration_snapshot,
)
from k_loto.domain.enums import DrawStatus, LotteryKind
from k_loto.domain.schedules import future_draw_target, next_draw_at, sales_close_at
from k_loto.infrastructure.database.models import Draw, JackpotAccount, Lottery

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    settled_draw_ids: tuple[UUID, ...]
    prepared_draw_ids: tuple[UUID, ...]


class DrawScheduleService:
    """Keep the required number of future draws ready under a lottery row lock."""

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
            pending_query = (
                select(Draw)
                .where(
                    Draw.lottery_id == lottery.id,
                    Draw.status != DrawStatus.COMPLETED,
                    Draw.sales_close_at > reference,
                )
                .order_by(Draw.scheduled_at)
            )
            target = future_draw_target(lottery.kind, lottery.schedule)
            if target == 1:
                pending = await self._session.scalar(pending_query.limit(1))
                if pending is not None:
                    return pending, False
                pending_draws: list[Draw] = []
            else:
                pending_draws = list((await self._session.scalars(pending_query)).all())
            if len(pending_draws) >= target:
                return pending_draws[0], False

            jackpot = await self._session.scalar(
                select(JackpotAccount).where(JackpotAccount.lottery_id == lottery.id)
            )
            if jackpot is None:
                raise LookupError("Lottery jackpot does not exist.")

            latest = await self._session.scalar(
                select(Draw)
                .where(Draw.lottery_id == lottery.id)
                .order_by(Draw.scheduled_at.desc())
                .limit(1)
            )
            schedule_base = latest.scheduled_at if latest is not None else reference
            created: list[Draw] = []
            while len(pending_draws) < target:
                scheduled_at = next_draw_at(
                    lottery.kind, schedule_base, lottery.schedule
                )
                draw = Draw(
                    id=uuid4(),
                    lottery_id=lottery.id,
                    public_number=lottery.next_draw_number,
                    status=DrawStatus.SCHEDULED,
                    scheduled_at=scheduled_at,
                    sales_close_at=sales_close_at(
                        lottery.kind, scheduled_at, lottery.sales_cutoff_minutes
                    ),
                    correlation_id=uuid4(),
                    ticket_count=0,
                    total_sales=0,
                    total_payout=0,
                    reserve_used=0,
                    kasper_fund_used=0,
                    configuration_snapshot=draw_configuration_snapshot(
                        lottery, jackpot.base_amount
                    ),
                )
                lottery.next_draw_number += 1
                self._session.add(draw)
                pending_draws.append(draw)
                created.append(draw)
                schedule_base = scheduled_at
        return created[0], True


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

    async def _next_due_draw(self, now: datetime) -> UUID | None:
        async with self._session_factory() as session:
            draw_id = await session.scalar(
                select(Draw.id)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .where(
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

    async def _lottery_kind_for_draw(self, draw_id: UUID) -> LotteryKind:
        """Compatibility diagnostic; settlement itself now resolves persisted rules."""
        async with self._session_factory() as session:
            kind = await session.scalar(
                select(Lottery.kind)
                .join(Draw, Draw.lottery_id == Lottery.id)
                .where(Draw.id == draw_id)
            )
        if kind is None:
            raise LookupError("Draw lottery disappeared from business history.")
        return kind

    async def _lottery_is_active(self, lottery_id: UUID) -> bool:
        async with self._session_factory() as session:
            active = await session.scalar(
                select(Lottery.is_active).where(Lottery.id == lottery_id)
            )
        return bool(active)

    async def reconcile(self, *, now: datetime | None = None) -> RecoveryReport:
        timestamp = now or datetime.now(UTC)
        prepared: list[UUID] = []
        settled: list[UUID] = []

        async with self._session_factory() as session:
            await DailyTransitionService(session).finalize_if_ready()

        for lottery_id in await self._active_lottery_ids():
            async with self._session_factory() as session:
                draw, created = await DrawScheduleService(session).ensure_next_draw(
                    lottery_id, reference=timestamp
                )
                if created:
                    prepared.append(draw.id)

        while due_draw_id := await self._next_due_draw(timestamp):
            async with self._session_factory() as session:
                service = LotterySettlementService(session)
                result = await service.settle(due_draw_id, now=timestamp)
            if not result.already_completed:
                settled.append(due_draw_id)

            async with self._session_factory() as session:
                await DailyTransitionService(session).finalize_if_ready()

            lottery_id = await self._lottery_id_for_draw(due_draw_id)
            if not await self._lottery_is_active(lottery_id):
                continue
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
