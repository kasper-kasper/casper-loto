"""Enable Fast live presentation and backfill Fast jackpot history.

Revision ID: 0026_fast_live
Revises: 0025_add_daily_slots
Create Date: 2026-09-04
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0026_fast_live"
down_revision: str | Sequence[str] | None = "0025_add_daily_slots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE lotteries
            SET schedule = jsonb_set(schedule, '{live_enabled}', 'true'::jsonb, true)
            WHERE code IN ('flash', 'shadow')
            """
        )
    )
    rows = (
        connection.execute(
            sa.text(
                """
                SELECT
                    d.id AS draw_id,
                    d.lottery_id,
                    d.jackpot_opening AS jackpot_amount,
                    COUNT(t.id) AS winner_ticket_count,
                    COUNT(DISTINCT t.user_id) AS winner_user_count,
                    d.jackpot_closing AS base_jackpot_after,
                    COALESCE(d.executed_at, d.scheduled_at) AS occurred_at
                FROM draws AS d
                JOIN lotteries AS l ON l.id = d.lottery_id
                JOIN tickets AS t ON t.draw_id = d.id AND t.matches = 3
                LEFT JOIN jackpot_win_events AS e ON e.draw_id = d.id
                WHERE l.code IN ('flash', 'shadow')
                  AND d.status = 'COMPLETED'
                  AND d.jackpot_opening > 0
                  AND d.jackpot_closing IS NOT NULL
                  AND e.id IS NULL
                GROUP BY d.id
                ORDER BY d.scheduled_at
                """
            )
        )
        .mappings()
        .all()
    )
    for row in rows:
        connection.execute(
            sa.text(
                """
                INSERT INTO jackpot_win_events (
                    id, draw_id, lottery_id, jackpot_amount,
                    winner_ticket_count, winner_user_count,
                    base_jackpot_after, occurred_at
                ) VALUES (
                    :id, :draw_id, :lottery_id, :jackpot_amount,
                    :winner_ticket_count, :winner_user_count,
                    :base_jackpot_after, :occurred_at
                ) ON CONFLICT (draw_id) DO NOTHING
                """
            ),
            {"id": uuid4(), **dict(row)},
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE lotteries
            SET schedule = jsonb_set(schedule, '{live_enabled}', 'false'::jsonb, true)
            WHERE code IN ('flash', 'shadow')
            """
        )
    )
    # Jackpot events are immutable business history and are intentionally retained.
