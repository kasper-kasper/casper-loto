"""Add the second daily Kasper Bingo slot at 10:30 Moscow."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0047_bingo_second_daily_slot"
down_revision: str | Sequence[str] | None = "0046_casper_dual"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE lotteries
            SET schedule = jsonb_set(
                schedule,
                '{slots}',
                '["10:30", "22:00"]'::jsonb,
                true
            )
            WHERE code = 'bingo'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE lotteries
            SET schedule = jsonb_set(
                schedule,
                '{slots}',
                '["22:00"]'::jsonb,
                true
            )
            WHERE code = 'bingo'
            """
        )
    )
