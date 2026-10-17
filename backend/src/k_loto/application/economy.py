"""Shared, transaction-scoped gate for purchases and draw operations."""

from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.errors import InvalidStateTransition
from k_loto.infrastructure.database.models import EconomyControl

ECONOMY_LOCK = 754_736_201


async def control_state(session: AsyncSession) -> EconomyControl:
    control = await session.scalar(
        select(EconomyControl)
        .where(EconomyControl.id == 1)
        .execution_options(populate_existing=True)
    )
    if control is None:
        raise InvalidStateTransition("Economy control is missing; operations disabled.")
    return control


async def require_open(session: AsyncSession) -> EconomyControl:
    # Shared by all money/draw operations, exclusive during an owner transition.
    await session.execute(
        text("SELECT pg_advisory_xact_lock_shared(:key)"), {"key": ECONOMY_LOCK}
    )
    control = await control_state(session)
    if control.paused:
        raise InvalidStateTransition(
            "Обновляем экономику. Приложение временно закрыто."
        )
    return control


async def is_paused(session: AsyncSession) -> bool:
    return (await control_state(session)).paused


def schedule_checkpoint(base: datetime, control: EconomyControl) -> datetime:
    """Skip planned downtime, but still recover genuine missed draws after reopening."""
    return max(base, control.recovery_after) if control.recovery_after else base
