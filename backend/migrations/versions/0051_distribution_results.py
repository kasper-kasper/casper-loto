"""Unique schedule/result receipts; keep all existing announcement history."""

import sqlalchemy as sa
from alembic import op

revision = "0051_distribution_results"
down_revision = "0050_distribution_draws"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "distribution_announcements",
        sa.Column("kind", sa.String(16), nullable=False, server_default="schedule"),
    )
    op.drop_constraint(
        "uq_distribution_announcements_draw_id",
        "distribution_announcements",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_distribution_announcement_draw_kind",
        "distribution_announcements",
        ["draw_id", "kind"],
    )
    op.create_check_constraint(
        "distribution_announcement_kind",
        "distribution_announcements",
        "kind IN ('schedule','result')",
    )
    op.create_index(
        "ix_distribution_announcement_delivery",
        "distribution_announcements",
        ["state", "retry_after"],
    )


def downgrade() -> None:
    raise RuntimeError("Result publication receipts must be retained.")
