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
    op.drop_constraint("uq_draw_lottery_schedule", "draws", type_="unique")
    op.create_index(
        "uq_draw_active_lottery_schedule",
        "draws",
        ["lottery_id", "scheduled_at"],
        unique=True,
        postgresql_where=sa.text("status <> 'CANCELLED'"),
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_completed_draw_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.status IN ('COMPLETED', 'CANCELLED') THEN
                RAISE EXCEPTION 'completed or cancelled draws are immutable';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    # Removing cancellation or pause history would permit replay of retired slots.
    raise RuntimeError("Economy pause history cannot be downgraded.")
