"""Read-only Admin period filtering; business sessions always see full history."""

from datetime import datetime

from sqlalchemy import Integer, event, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, with_loader_criteria

from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    Draw,
    InstantTicket,
    JackpotWinEvent,
    LedgerTransaction,
    NotificationOutbox,
    Publication,
    Ticket,
)


def apply_archive_scope(
    session: AsyncSession, *, epoch: int, started_at: datetime | None, archive: bool
) -> None:
    session.info["economy_scope"] = (epoch, "archive" if archive else "current")
    if started_at is None:
        return
    epoch_value = func.coalesce(
        Draw.configuration_snapshot["economy_epoch"].astext, "1"
    ).cast(Integer)
    draw_condition = epoch_value < epoch if archive else epoch_value == epoch
    draw_ids = select(Draw.id).where(draw_condition)
    conditions = [(Draw, draw_condition), (Ticket, Ticket.draw_id.in_(draw_ids))]
    for model, field in (
        (InstantTicket, InstantTicket.purchased_at),
        (LedgerTransaction, LedgerTransaction.created_at),
        (JackpotWinEvent, JackpotWinEvent.occurred_at),
        (AdminAuditLog, AdminAuditLog.created_at),
        (NotificationOutbox, NotificationOutbox.created_at),
        (Publication, Publication.created_at),
    ):
        conditions.append(
            (model, field < started_at if archive else field >= started_at)
        )

    def scope_query(state: ORMExecuteState) -> None:
        if state.is_select:
            state.statement = state.statement.options(
                *(
                    with_loader_criteria(model, condition, include_aliases=True)
                    for model, condition in conditions
                )
            )

    event.listen(session.sync_session, "do_orm_execute", scope_query)
