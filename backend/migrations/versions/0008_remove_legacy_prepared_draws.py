"""Remove empty legacy draws recreated during the consolidation restart.

Revision ID: 0008_legacy_draw_cleanup
Revises: 0007_unified_daily_lottery
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_legacy_draw_cleanup"
down_revision: str | Sequence[str] | None = "0007_unified_daily_lottery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_completed_draw_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.status = 'COMPLETED' THEN
                RAISE EXCEPTION 'completed draws are immutable';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    live_ticket_count = connection.execute(
        sa.text(
            """
            SELECT count(*) FROM tickets t
            JOIN lotteries l ON l.id=t.lottery_id
            WHERE l.code IN ('pss', 'khan', 'pll') AND t.status='PURCHASED'
            """
        )
    ).scalar_one()
    if live_ticket_count:
        raise RuntimeError(
            "Cannot remove legacy prepared draws while their tickets are active."
        )
    connection.execute(
        sa.text(
            """
            DELETE FROM draws d USING lotteries l
            WHERE d.lottery_id=l.id
              AND l.code IN ('pss', 'khan', 'pll')
              AND d.status='SCHEDULED'
              AND NOT EXISTS (SELECT 1 FROM tickets t WHERE t.draw_id=d.id)
            """
        )
    )


def downgrade() -> None:
    # Prepared empty draws contain no business history and are regenerated only
    # for active lotteries. Legacy lotteries deliberately remain inactive.
    pass
