"""Persist scheduler health.

Revision ID: 0012_scheduler_heartbeat
Revises: 0011_operational_limits
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_scheduler_heartbeat"
down_revision: str | Sequence[str] | None = "0011_operational_limits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduler_heartbeat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_started_at", sa.DateTime(timezone=True)),
        sa.Column("last_succeeded_at", sa.DateTime(timezone=True)),
        sa.Column("last_failed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(length=256)),
        sa.Column("settled_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("prepared_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.execute(
        "INSERT INTO scheduler_heartbeat (id, settled_count, prepared_count) "
        "VALUES (1, 0, 0)"
    )


def downgrade() -> None:
    op.drop_table("scheduler_heartbeat")
