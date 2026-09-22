"""Add immediately settled Kasper LIVE tickets.

Revision ID: 0042_kasper_live
Revises: 0041_fast_prize_formats
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0042_kasper_live"
down_revision: str | Sequence[str] | None = "0041_fast_prize_formats"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instant_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "public_number",
            sa.BigInteger(),
            sa.Identity(always=False, start=1),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbols", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("purchase_price", sa.BigInteger(), nullable=False),
        sa.Column("prize_amount", sa.BigInteger(), nullable=False),
        sa.Column("odds_version", sa.String(length=32), nullable=False),
        sa.Column(
            "purchased_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "settled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("public_number >= 1", name="public_number_positive"),
        sa.CheckConstraint("purchase_price > 0", name="purchase_price_positive"),
        sa.CheckConstraint("prize_amount >= 0", name="prize_amount_nonnegative"),
        sa.CheckConstraint("cardinality(symbols) = 3", name="three_symbols"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_number"),
    )
    op.create_index(
        "ix_instant_ticket_user_purchased",
        "instant_tickets",
        ["user_id", "purchased_at"],
    )
    op.create_index("ix_instant_ticket_purchased", "instant_tickets", ["purchased_at"])


def downgrade() -> None:
    op.drop_index("ix_instant_ticket_purchased", table_name="instant_tickets")
    op.drop_index("ix_instant_ticket_user_purchased", table_name="instant_tickets")
    op.drop_table("instant_tickets")
