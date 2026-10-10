"""A jackpot cycle ends on a genuine win or a completed paid distribution."""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from k_loto.domain.enums import DrawStatus
from k_loto.infrastructure.database.models import Draw, JackpotWinEvent


def cycle_ended(draw: Draw, winning_draws: Collection[UUID]) -> bool:
    return draw.id in winning_draws or (draw.distributed_amount or 0) > 0


def cycle_end_filter() -> ColumnElement[bool]:
    won = select(JackpotWinEvent.id).where(JackpotWinEvent.draw_id == Draw.id).exists()
    return or_(Draw.distributed_amount > 0, won)


def last_cycle_ends() -> Subquery:
    return (
        select(Draw.lottery_id, func.max(Draw.scheduled_at).label("last_reset"))
        .where(Draw.status == DrawStatus.COMPLETED, cycle_end_filter())
        .group_by(Draw.lottery_id)
        .subquery()
    )
