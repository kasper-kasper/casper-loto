"""Independent in-app notification preference and re-enable boundary."""

import sqlalchemy as sa
from alembic import op

revision = "0068_in_app_notifications"
down_revision = "0067_new_year_2027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_notification_preferences",
        sa.Column(
            "in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column(
        "user_notification_preferences",
        sa.Column("in_app_enabled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_notification_preferences", "in_app_enabled_at")
    op.drop_column("user_notification_preferences", "in_app_enabled")
