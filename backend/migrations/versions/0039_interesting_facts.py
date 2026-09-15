"""Persist daily interesting-fact candidates.

Revision ID: 0039_interesting_facts
Revises: 0038_kasper_fast_formats
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0039_interesting_facts"
down_revision: str | Sequence[str] | None = "0038_kasper_fast_formats"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_ticket_status_settled_lottery",
        "tickets",
        ["status", "settled_at", "lottery_id"],
    )
    op.create_table(
        "interesting_fact_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generation_date", sa.Date(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generation_date"),
    )
    op.create_table(
        "interesting_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generation_date", sa.Date(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("lottery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fact_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.String(length=600), nullable=False),
        sa.Column(
            "numeric_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="new", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="score_valid"),
        sa.CheckConstraint(
            "status IN ('new', 'viewed', 'used', 'hidden')",
            name="interesting_fact_status",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"], ["interesting_fact_batches.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["lottery_id"], ["lotteries.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "generation_date",
            "lottery_id",
            "fact_type",
            name="uq_interesting_fact_daily_type",
        ),
    )
    op.create_index(
        "ix_interesting_facts_admin",
        "interesting_facts",
        ["status", "generation_date", "score"],
    )
    op.create_index(
        "ix_interesting_facts_lottery",
        "interesting_facts",
        ["lottery_id", "generation_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_interesting_facts_lottery", table_name="interesting_facts")
    op.drop_index("ix_interesting_facts_admin", table_name="interesting_facts")
    op.drop_table("interesting_facts")
    op.drop_table("interesting_fact_batches")
    op.drop_index("ix_ticket_status_settled_lottery", table_name="tickets")
