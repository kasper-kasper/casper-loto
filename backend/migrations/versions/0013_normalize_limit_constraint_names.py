"""Normalize purchase limit constraint names.

Revision ID: 0013_normalize_limit_constraints
Revises: 0012_scheduler_heartbeat
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013_normalize_limit_constraints"
down_revision: str | Sequence[str] | None = "0012_scheduler_heartbeat"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE lotteries RENAME CONSTRAINT "
        "ck_lotteries_ck_lotteries_max_tickets_per_purchase_valid "
        "TO ck_lotteries_max_tickets_per_purchase_valid"
    )
    op.execute(
        "ALTER TABLE lotteries RENAME CONSTRAINT "
        "ck_lotteries_ck_lotteries_max_tickets_per_user_per_draw_valid "
        "TO ck_lotteries_max_tickets_per_user_per_draw_valid"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE lotteries RENAME CONSTRAINT "
        "ck_lotteries_max_tickets_per_user_per_draw_valid "
        "TO ck_lotteries_ck_lotteries_max_tickets_per_user_per_draw_valid"
    )
    op.execute(
        "ALTER TABLE lotteries RENAME CONSTRAINT "
        "ck_lotteries_max_tickets_per_purchase_valid "
        "TO ck_lotteries_ck_lotteries_max_tickets_per_purchase_valid"
    )
