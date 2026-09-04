"""Restore the eight-second cutoff after production bootstrap.

Revision ID: 0030_fast_cutoff_fix
Revises: 0029_fast_cutoff
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_fast_cutoff_fix"
down_revision: str | Sequence[str] | None = "0029_fast_cutoff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE lotteries
            SET schedule = schedule || '{"sales_cutoff_seconds": 8}'::jsonb
            WHERE code IN ('flash', 'shadow', 'pulse')
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE draws
            SET sales_close_at = scheduled_at - INTERVAL '8 seconds'
            WHERE lottery_id IN (
                SELECT id FROM lotteries WHERE code IN ('flash', 'shadow', 'pulse')
            )
              AND scheduled_at > CURRENT_TIMESTAMP
              AND status = 'SCHEDULED'
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE lotteries
            SET schedule = schedule - 'sales_cutoff_seconds'
            WHERE code IN ('flash', 'shadow', 'pulse')
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE draws
            SET sales_close_at = scheduled_at - INTERVAL '1 minute'
            WHERE lottery_id IN (
                SELECT id FROM lotteries WHERE code IN ('flash', 'shadow', 'pulse')
            )
              AND scheduled_at > CURRENT_TIMESTAMP
              AND status = 'SCHEDULED'
            """
        )
    )
