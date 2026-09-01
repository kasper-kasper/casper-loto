"""Attach lotteries to reusable rule strategies.

Revision ID: 0018_lottery_rulesets
Revises: 0017_cancel_legacy_notices
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_lottery_rulesets"
down_revision: str | Sequence[str] | None = "0017_cancel_legacy_notices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("lotteries", sa.Column("ruleset_code", sa.String(64), nullable=True))
    op.execute(
        "UPDATE lotteries SET ruleset_code = CASE WHEN kind = 'WEEKLY' "
        "THEN 'weekly_5_20' ELSE 'daily_4_15' END"
    )
    op.alter_column("lotteries", "ruleset_code", nullable=False)
    op.create_check_constraint(
        "ruleset_code_not_empty", "lotteries", "char_length(ruleset_code) > 0"
    )
    op.create_index("ix_lotteries_ruleset_code", "lotteries", ["ruleset_code"])


def downgrade() -> None:
    op.drop_index("ix_lotteries_ruleset_code", table_name="lotteries")
    op.drop_constraint("ruleset_code_not_empty", "lotteries", type_="check")
    op.drop_column("lotteries", "ruleset_code")
