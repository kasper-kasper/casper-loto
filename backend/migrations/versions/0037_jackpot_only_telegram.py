"""Limit player Telegram delivery to jackpot wins and reminders.

Revision ID: 0037_jackpot_only_telegram
Revises: 0036_bingo_prizes_and_numbering
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037_jackpot_only_telegram"
down_revision: str | Sequence[str] | None = "0036_bingo_prizes_and_numbering"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NOTIFICATION_TYPES = (
    "'TICKET_PURCHASED', 'DRAW_RESULT', 'JACKPOT_WIN', "
    "'INACTIVITY_REMINDER', 'DELIVERY_TEST', 'SYSTEM_ALERT'"
)
LEGACY_NOTIFICATION_TYPES = (
    "'TICKET_PURCHASED', 'DRAW_RESULT', 'INACTIVITY_REMINDER', "
    "'DELIVERY_TEST', 'SYSTEM_ALERT'"
)


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_notification_outbox_notification_type"),
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "notification_type",
        "notification_outbox",
        f"type IN ({NOTIFICATION_TYPES})",
    )
    op.execute(
        "UPDATE notification_outbox SET status = 'CANCELLED', locked_at = NULL "
        "WHERE type IN ('TICKET_PURCHASED', 'DRAW_RESULT') "
        "AND status IN ('PENDING', 'PROCESSING', 'FAILED')"
    )


def downgrade() -> None:
    connection = op.get_bind()
    jackpot_rows = connection.scalar(
        sa.text("SELECT count(*) FROM notification_outbox WHERE type = 'JACKPOT_WIN'")
    )
    if jackpot_rows:
        raise RuntimeError("JACKPOT_WIN notification history prevents safe downgrade.")
    op.drop_constraint(
        op.f("ck_notification_outbox_notification_type"),
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "notification_type",
        "notification_outbox",
        f"type IN ({LEGACY_NOTIFICATION_TYPES})",
    )
