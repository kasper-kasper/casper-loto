"""Add one-time Telegram-to-Web login tokens.

Revision ID: 0005_telegram_web_login
Revises: 0004_constraint_names
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_telegram_web_login"
down_revision: str | Sequence[str] | None = "0004_constraint_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "web_login_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("token_hash", name="uq_web_login_tokens_token_hash"),
        sa.CheckConstraint(
            "char_length(token_hash) = 64",
            name=op.f("ck_web_login_tokens_token_hash_length"),
        ),
    )
    op.create_index(
        "ix_web_login_tokens_expires_at", "web_login_tokens", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_web_login_tokens_expires_at", table_name="web_login_tokens")
    op.drop_table("web_login_tokens")
