"""Normalize the auto-play ticket-limit constraint name.

Revision ID: 0015_normalize_auto_play_ck
Revises: 0014_player_inbox_auto_play
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0015_normalize_auto_play_ck"
down_revision: str | Sequence[str] | None = "0014_player_inbox_auto_play"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE auto_play_settings RENAME CONSTRAINT "
        "ck_auto_play_settings_ck_auto_play_settings_tickets_per_10cf "
        "TO ck_auto_play_settings_tickets_per_draw_valid"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE auto_play_settings RENAME CONSTRAINT "
        "ck_auto_play_settings_tickets_per_draw_valid "
        "TO ck_auto_play_settings_ck_auto_play_settings_tickets_per_10cf"
    )
