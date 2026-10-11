"""Indexes for player ticket groups and upcoming lottery draws."""

from alembic import op

revision = "0052_read_path_indexes"
down_revision = "0051_distribution_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Production purchases continue during construction; never lock the full
    # ticket table for the duration of an ordinary CREATE INDEX.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_ticket_user_draw_status",
            "tickets",
            ["user_id", "draw_id", "status"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_draw_lottery_status_scheduled",
            "draws",
            ["lottery_id", "status", "scheduled_at"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_draw_lottery_status_scheduled",
            table_name="draws",
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_ticket_user_draw_status",
            table_name="tickets",
            postgresql_concurrently=True,
        )
