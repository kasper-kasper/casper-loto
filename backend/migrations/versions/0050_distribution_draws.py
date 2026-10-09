"""Explicit distribution draw policy and durable text-only announcement outbox."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0050_distribution_draws"
down_revision = "0049_publication_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "draws",
        sa.Column(
            "is_distribution", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "draws", sa.Column("distribution_category", sa.String(32), nullable=True)
    )
    op.add_column(
        "draws",
        sa.Column(
            "distributed_amount", sa.BigInteger(), nullable=False, server_default="0"
        ),
    )
    op.create_check_constraint(
        "distributed_amount_nonnegative", "draws", "distributed_amount >= 0"
    )
    op.create_table(
        "distribution_announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "draw_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("draws.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("retry_after", sa.DateTime(timezone=True)),
        sa.Column("message_id", sa.BigInteger()),
        sa.Column("error_type", sa.String(100)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "state IN ('queued','sending','sent','uncertain','failed','expired')",
            name="ck_distribution_announcement_state",
        ),
    )


def downgrade() -> None:
    raise RuntimeError(
        "Distribution decisions and announcement receipts are immutable."
    )
