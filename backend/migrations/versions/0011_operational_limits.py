"""Add configurable purchase safety limits.

Revision ID: 0011_operational_limits
Revises: 0010_independent_daily
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_operational_limits"
down_revision: str | Sequence[str] | None = "0010_independent_daily"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lotteries",
        sa.Column(
            "max_tickets_per_purchase",
            sa.Integer(),
            server_default="1000",
            nullable=False,
        ),
    )
    op.add_column(
        "lotteries",
        sa.Column(
            "max_tickets_per_user_per_draw",
            sa.Integer(),
            server_default="5000",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_lotteries_max_tickets_per_purchase_valid",
        "lotteries",
        "max_tickets_per_purchase BETWEEN 1 AND 1000",
    )
    op.create_check_constraint(
        "ck_lotteries_max_tickets_per_user_per_draw_valid",
        "lotteries",
        "max_tickets_per_user_per_draw >= max_tickets_per_purchase",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_lotteries_max_tickets_per_user_per_draw_valid",
        "lotteries",
        type_="check",
    )
    op.drop_constraint(
        "ck_lotteries_max_tickets_per_purchase_valid",
        "lotteries",
        type_="check",
    )
    op.drop_column("lotteries", "max_tickets_per_user_per_draw")
    op.drop_column("lotteries", "max_tickets_per_purchase")
