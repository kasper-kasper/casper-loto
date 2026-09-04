"""Align Fast sales cutoff with the compact live presentation.

Revision ID: 0029_fast_cutoff
Revises: 0028_pulse_fast
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_fast_cutoff"
down_revision: str | Sequence[str] | None = "0028_pulse_fast"
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
              AND status IN ('SCHEDULED', 'CLOSED')
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
              AND status IN ('SCHEDULED', 'CLOSED')
            """
        )
    )
