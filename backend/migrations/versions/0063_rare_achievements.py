"""Winning-ticket counts in sparse achievement draw projections."""

import sqlalchemy as sa
from alembic import op

revision = "0063_rare_achievements"
down_revision = "0062_uncommon_achievements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "achievement_winning_draws",
        sa.Column("tickets", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "tickets_nonnegative", "achievement_winning_draws", "tickets >= 0"
    )


def downgrade() -> None:
    raise RuntimeError("Preserve achievement progress; use a forward migration")
