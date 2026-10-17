"""Persist planned economy pauses and preserve cancelled draw numbers."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0057_economy_pause"
down_revision = "0056_player_profile_projection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "economy_control",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("pause_started_at", sa.DateTime(timezone=True)),
        sa.Column("recovery_after", sa.DateTime(timezone=True)),
        sa.Column("epoch", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("epoch_started_at", sa.DateTime(timezone=True)),
        sa.Column(
            "applied_steps", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.CheckConstraint("id = 1", name="singleton"),
    )
    op.execute("INSERT INTO economy_control(id) VALUES (1)")
    op.add_column(
        "lotteries",
        sa.Column("economy_epoch", sa.Integer(), nullable=False, server_default="1"),
    )
    op.drop_constraint(op.f("ck_draws_draw_status"), "draws", type_="check")
    op.create_check_constraint(
        "draw_status",
        "draws",
        "status IN ('SCHEDULED','CLOSED','DRAWING','SETTLING',"
        "'COMPLETED','FAILED','CANCELLED')",
    )


def downgrade() -> None:
    # Removing cancellation or pause history would permit replay of retired slots.
    raise RuntimeError("Economy pause history cannot be downgraded.")
