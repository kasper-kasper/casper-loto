"""Add player inbox, notification consent and auto play.

Revision ID: 0014_player_inbox_auto_play
Revises: 0013_normalize_limit_constraints
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_player_inbox_auto_play"
down_revision: str | Sequence[str] | None = "0013_normalize_limit_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column(
            "source", sa.String(length=32), server_default="MANUAL", nullable=False
        ),
    )
    op.create_check_constraint(
        "ticket_source", "tickets", "source IN ('MANUAL', 'AUTO_PLAY')"
    )
    op.drop_constraint(
        "ck_notification_outbox_notification_type",
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "notification_type",
        "notification_outbox",
        "type IN ('TICKET_PURCHASED', 'DRAW_RESULT', 'INACTIVITY_REMINDER')",
    )

    op.create_table(
        "user_notification_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "telegram_enabled", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "draw_results_enabled", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "inactivity_reminders_enabled",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column("write_access_granted_at", sa.DateTime(timezone=True)),
        sa.Column("last_inactivity_reminder_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.execute(
        "INSERT INTO user_notification_preferences (user_id) "
        "SELECT id FROM users WHERE is_admin = false"
    )
    op.create_table(
        "user_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_key", sa.String(length=180), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.String(length=512), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("event_key", name="uq_user_notifications_event_key"),
        sa.CheckConstraint(
            "type IN ('WIN', 'DRAW_INVITATION')",
            name="ck_user_notifications_in_app_notification_type",
        ),
    )
    op.create_index(
        "ix_user_notification_inbox",
        "user_notifications",
        ["user_id", "created_at"],
    )
    op.create_table(
        "auto_play_settings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("tickets_per_draw", sa.Integer(), server_default="5", nullable=False),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True)),
        sa.Column("last_succeeded_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(length=128)),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "tickets_per_draw BETWEEN 1 AND 5",
            name="ck_auto_play_settings_tickets_per_draw_valid",
        ),
    )
    op.execute(
        """
        CREATE FUNCTION protect_user_notification() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'user notification history cannot be deleted';
            END IF;
            IF OLD.event_key IS DISTINCT FROM NEW.event_key
               OR OLD.user_id IS DISTINCT FROM NEW.user_id
               OR OLD.type IS DISTINCT FROM NEW.type
               OR OLD.title IS DISTINCT FROM NEW.title
               OR OLD.body IS DISTINCT FROM NEW.body
               OR OLD.payload IS DISTINCT FROM NEW.payload
               OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
                RAISE EXCEPTION 'user notification content is immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_user_notification_immutable
        BEFORE UPDATE OR DELETE ON user_notifications
        FOR EACH ROW EXECUTE FUNCTION protect_user_notification();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_notification_immutable ON user_notifications"
    )
    op.execute("DROP FUNCTION IF EXISTS protect_user_notification")
    op.drop_table("auto_play_settings")
    op.drop_index("ix_user_notification_inbox", table_name="user_notifications")
    op.drop_table("user_notifications")
    op.drop_table("user_notification_preferences")
    op.drop_constraint(
        "ck_notification_outbox_notification_type",
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "notification_type",
        "notification_outbox",
        "type IN ('TICKET_PURCHASED', 'DRAW_RESULT')",
    )
    op.drop_constraint("ck_tickets_ticket_source", "tickets", type_="check")
    op.drop_column("tickets", "source")
