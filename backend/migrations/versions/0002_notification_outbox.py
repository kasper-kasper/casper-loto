"""Add durable Telegram notification outbox.

Revision ID: 0002_notification_outbox
Revises: 0001_domain_model
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_notification_outbox"
down_revision: str | Sequence[str] | None = "0001_domain_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
    )


def upgrade() -> None:
    op.create_table(
        "notification_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_key", sa.String(180), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type",
            enum("notification_type", "TICKET_PURCHASED", "DRAW_RESULT"),
            nullable=False,
        ),
        sa.Column(
            "status",
            enum("notification_status", "PENDING", "PROCESSING", "SENT", "FAILED"),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("event_key", name="uq_notification_outbox_event_key"),
        sa.CheckConstraint(
            "attempts >= 0", name="ck_notification_outbox_attempts_nonnegative"
        ),
    )
    op.create_index(
        "ix_notification_outbox_dispatch",
        "notification_outbox",
        ["status", "available_at"],
    )
    op.execute(
        """
        CREATE FUNCTION protect_notification_event() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'notification outbox history cannot be deleted';
            END IF;
            IF OLD.event_key IS DISTINCT FROM NEW.event_key
               OR OLD.user_id IS DISTINCT FROM NEW.user_id
               OR OLD.type IS DISTINCT FROM NEW.type
               OR OLD.payload IS DISTINCT FROM NEW.payload
               OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
                RAISE EXCEPTION 'notification event payload is immutable';
            END IF;
            IF OLD.status = 'SENT' THEN
                RAISE EXCEPTION 'sent notification is immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_notification_event_immutable
        BEFORE UPDATE OR DELETE ON notification_outbox
        FOR EACH ROW EXECUTE FUNCTION protect_notification_event();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_notification_event_immutable ON notification_outbox"
    )
    op.execute("DROP FUNCTION IF EXISTS protect_notification_event")
    op.drop_table("notification_outbox")
