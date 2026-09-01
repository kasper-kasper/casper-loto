"""Add three approved draw slots to existing Daily lotteries.

Revision ID: 0025_add_daily_slots
Revises: 0024_fast_lotteries
Create Date: 2026-09-02
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_add_daily_slots"
down_revision: str | Sequence[str] | None = "0024_fast_lotteries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEDULES = {
    "khan": ["09:00", "18:00"],
    "pll": ["02:22", "13:45"],
    "pss": ["12:00", "20:30"],
}
ORIGINAL_SCHEDULES = {
    "khan": {"draw_time": "18:00"},
    "pll": {"draw_time": "02:22"},
    "pss": {"draw_time": "12:00"},
}


def upgrade() -> None:
    connection = op.get_bind()
    for code, slots in SCHEDULES.items():
        connection.execute(
            sa.text(
                "UPDATE lotteries SET schedule=CAST(:schedule AS jsonb) "
                "WHERE code=:code"
            ),
            {"code": code, "schedule": json.dumps({"slots": slots})},
        )


def downgrade() -> None:
    connection = op.get_bind()
    for code, schedule in ORIGINAL_SCHEDULES.items():
        connection.execute(
            sa.text(
                "UPDATE lotteries SET schedule=CAST(:schedule AS jsonb) "
                "WHERE code=:code"
            ),
            {"code": code, "schedule": json.dumps(schedule)},
        )
