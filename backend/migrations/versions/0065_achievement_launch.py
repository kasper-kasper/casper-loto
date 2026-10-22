"""Explicit scheduled production launch and processing-only emergency pause."""

import sqlalchemy as sa
from alembic import op

revision = "0065_achievement_launch"
down_revision = "0064_legendary_collections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "achievement_runtime", sa.Column("scheduled_at", sa.DateTime(timezone=True))
    )
    op.add_column("achievement_runtime", sa.Column("scheduled_revision", sa.Integer()))
    op.add_column(
        "achievement_runtime",
        sa.Column(
            "processing_paused", sa.Boolean(), nullable=False, server_default="false"
        ),
    )


def downgrade() -> None:
    raise RuntimeError("Achievement launch state requires a forward migration")
