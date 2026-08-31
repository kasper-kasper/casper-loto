"""Add reusable player number combinations.

Revision ID: 0009_favorite_combinations
Revises: 0008_legacy_draw_cleanup
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_favorite_combinations"
down_revision: str | Sequence[str] | None = "0008_legacy_draw_cleanup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "favorite_combinations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lottery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numbers", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("cardinality(numbers) > 0", name="numbers_not_empty"),
        sa.ForeignKeyConstraint(["lottery_id"], ["lotteries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "lottery_id",
            "numbers",
            name="uq_favorite_user_lottery_numbers",
        ),
    )
    op.create_index(
        "ix_favorite_user_lottery",
        "favorite_combinations",
        ["user_id", "lottery_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_favorite_user_lottery", table_name="favorite_combinations")
    op.drop_table("favorite_combinations")
