"""Compact entitlements; one immutable child reward per issued ticket, on demand."""

from datetime import UTC, datetime, timedelta
from uuid import uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementReward,
)


async def deliver_pack(
    session: AsyncSession, award: AchievementAward, part: AchievementReward
) -> None:
    from k_loto.application.achievements import deliver_ticket

    total = int(part.payload["amount"])
    if not 1 <= total <= 500 or part.parent_id is not None or part.position >= 16:
        raise ValueError("Invalid compact gift package")
    if part.completed_units >= total:
        return
    ordinal = part.completed_units
    # Fixed disjoint position ranges preserve the original award/part constraint.
    unit = AchievementReward(
        id=uuid5(part.id, f"gift-unit:{ordinal}"),
        award_id=award.id,
        parent_id=part.id,
        position=16 + part.position * 1000 + ordinal,
        payload={"type": "ticket", "lottery": part.payload["lottery"], "amount": 1},
        status="pending",
    )
    session.add(unit)
    await session.flush()
    await deliver_ticket(session, award, unit)
    unit.status, unit.completed_at = "completed", datetime.now(UTC)
    part.completed_units += 1
    if part.completed_units < total:
        # Yield after one purchase/ledger transaction; next retry has a new event ID.
        part.status, part.retry_at = (
            "waiting",
            datetime.now(UTC) + timedelta(milliseconds=100),
        )
