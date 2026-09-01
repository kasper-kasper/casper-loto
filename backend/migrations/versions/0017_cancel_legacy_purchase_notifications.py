"""Stop obsolete purchase notifications that cannot be delivered.

Revision ID: 0017_cancel_legacy_notices
Revises: 0016_operational_notifications
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0017_cancel_legacy_notices"
down_revision: str | Sequence[str] | None = "0016_operational_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_notification_outbox_notification_status"),
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "notification_status",
        "notification_outbox",
        "status IN ('PENDING', 'PROCESSING', 'SENT', 'FAILED', 'CANCELLED')",
    )
    op.execute(
        "UPDATE notification_outbox SET status = 'CANCELLED', locked_at = NULL "
        "WHERE type = 'TICKET_PURCHASED' "
        "AND status IN ('PENDING', 'PROCESSING', 'FAILED')"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE notification_outbox SET status = 'FAILED' WHERE status = 'CANCELLED'"
    )
    op.drop_constraint(
        op.f("ck_notification_outbox_notification_status"),
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "notification_status",
        "notification_outbox",
        "status IN ('PENDING', 'PROCESSING', 'SENT', 'FAILED')",
    )
