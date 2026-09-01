"""Add delivery diagnostics and owner operational alerts.

Revision ID: 0016_operational_notifications
Revises: 0015_normalize_auto_play_ck
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0016_operational_notifications"
down_revision: str | Sequence[str] | None = "0015_normalize_auto_play_ck"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_notification_outbox_notification_type"),
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "notification_type",
        "notification_outbox",
        "type IN ('TICKET_PURCHASED', 'DRAW_RESULT', 'INACTIVITY_REMINDER', "
        "'DELIVERY_TEST', 'SYSTEM_ALERT')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_notification_outbox_notification_type"),
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "notification_type",
        "notification_outbox",
        "type IN ('TICKET_PURCHASED', 'DRAW_RESULT', 'INACTIVITY_REMINDER')",
    )
