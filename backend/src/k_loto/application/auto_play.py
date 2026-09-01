"""Idempotent recurring entry for explicitly configured players."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.application.daily import DailyTicketPurchaseService
from k_loto.application.weekly import WeeklyTicketPurchaseService
from k_loto.domain.enums import DrawStatus, LotteryKind, TicketSource
from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InvalidTicket,
    NoAvailableDraw,
)
from k_loto.domain.lotteries import FAST_LOTTERY_CODES
from k_loto.domain.weekly import SystemRandomNumberGenerator
from k_loto.infrastructure.database.models import (
    AutoPlaySetting,
    Draw,
    Lottery,
    Ticket,
    User,
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AutoPlayCandidate:
    user_id: UUID
    draw_id: UUID
    lottery_code: str
    lottery_kind: LotteryKind
    numbers_to_pick: int
    max_number: int
    tickets_per_draw: int


@dataclass(frozen=True, slots=True)
class AutoPlayReport:
    purchased_draw_ids: tuple[UUID, ...]
    failed_draw_ids: tuple[UUID, ...]


class AutoPlayService:
    """Buy configured random entries once for every open draw."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        number_generator: SystemRandomNumberGenerator | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._number_generator = number_generator or SystemRandomNumberGenerator()

    async def _candidates(self, now: datetime) -> tuple[AutoPlayCandidate, ...]:
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(AutoPlaySetting, Draw, Lottery)
                    .join(User, User.id == AutoPlaySetting.user_id)
                    .join(Lottery, Lottery.is_active.is_(True))
                    .join(
                        Draw,
                        (Draw.lottery_id == Lottery.id)
                        & (Draw.status == DrawStatus.SCHEDULED)
                        & (Draw.sales_close_at > now),
                    )
                    .where(
                        AutoPlaySetting.enabled.is_(True),
                        User.is_active.is_(True),
                        User.is_admin.is_(False),
                        Lottery.code.not_in(FAST_LOTTERY_CODES),
                        ~exists(
                            select(Ticket.id).where(
                                Ticket.user_id == AutoPlaySetting.user_id,
                                Ticket.draw_id == Draw.id,
                                Ticket.source == TicketSource.AUTO_PLAY,
                            )
                        ),
                    )
                    .order_by(Draw.scheduled_at, AutoPlaySetting.user_id)
                )
            ).all()
        return tuple(
            AutoPlayCandidate(
                setting.user_id,
                draw.id,
                lottery.code,
                lottery.kind,
                lottery.numbers_to_pick,
                lottery.max_number,
                setting.tickets_per_draw,
            )
            for setting, draw, lottery in rows
        )

    async def _record_attempt(
        self, user_id: UUID, now: datetime, error: str | None
    ) -> None:
        async with self._session_factory() as session, session.begin():
            setting = await session.get(AutoPlaySetting, user_id)
            if setting is None:
                return
            setting.last_attempted_at = now
            setting.last_error = error
            if error is None:
                setting.last_succeeded_at = now

    async def run(self, *, now: datetime | None = None) -> AutoPlayReport:
        timestamp = now or datetime.now(UTC)
        purchased: list[UUID] = []
        failed: list[UUID] = []
        for candidate in await self._candidates(timestamp):
            combinations: list[list[int] | tuple[int, ...]] = [
                list(
                    self._number_generator.draw(
                        candidate.max_number, candidate.numbers_to_pick
                    )
                )
                for _ in range(candidate.tickets_per_draw)
            ]
            service_type = (
                DailyTicketPurchaseService
                if candidate.lottery_kind == LotteryKind.DAILY
                else WeeklyTicketPurchaseService
            )
            try:
                async with self._session_factory() as session:
                    await service_type(
                        session,
                        candidate.lottery_code,
                        target_draw_id=candidate.draw_id,
                    ).purchase(
                        user_id=candidate.user_id,
                        combinations=combinations,
                        idempotency_key=(
                            f"auto:{candidate.user_id.hex}:{candidate.draw_id.hex}"
                        ),
                        source=TicketSource.AUTO_PLAY,
                        now=timestamp,
                    )
            except (
                ConfigurationError,
                InsufficientBalance,
                InvalidTicket,
                NoAvailableDraw,
            ) as error:
                error_code = type(error).__name__[:128]
                await self._record_attempt(candidate.user_id, timestamp, error_code)
                failed.append(candidate.draw_id)
                logger.warning(
                    "auto_play_skipped",
                    user_id=str(candidate.user_id),
                    draw_id=str(candidate.draw_id),
                    error_code=error_code,
                )
                continue
            await self._record_attempt(candidate.user_id, timestamp, None)
            purchased.append(candidate.draw_id)
        return AutoPlayReport(tuple(purchased), tuple(failed))
