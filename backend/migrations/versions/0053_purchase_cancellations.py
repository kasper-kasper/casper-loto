"""Fences for explicitly cancelled, uncommitted Mini App requests."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0053_purchase_cancellations"
down_revision = "0052_read_path_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "purchase_cancellations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("game", sa.String(32), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "user_id", "game", "key", name="uq_purchase_cancellations_user_id_game_key"
        ),
    )


def downgrade() -> None:
    op.drop_table("purchase_cancellations")
