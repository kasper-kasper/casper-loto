"""Extend existing editorial drafts with nonvisual events and checkpoints."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0049_publication_events"
down_revision = "0048_manual_publications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("publications", sa.Column("event_type", sa.String(12)))
    op.add_column("publications", sa.Column("event_key", sa.String(180)))
    op.add_column("publications", sa.Column("event_mode", sa.String(16)))
    op.create_unique_constraint(
        "uq_publication_event_key", "publications", ["event_key"]
    )
    op.create_check_constraint(
        "publication_event_mode",
        "publications",
        "event_mode IS NULL OR event_mode IN ('automatic', 'draft')",
    )
    op.create_index(
        "ix_publications_event_type", "publications", ["event_type", "created_at"]
    )
    op.create_table(
        "publication_event_states",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    raise RuntimeError("Preserve editorial history; use a forward migration.")
