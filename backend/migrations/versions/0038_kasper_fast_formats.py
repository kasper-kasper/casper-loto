"""Refresh FLASH and PULSE while preserving already scheduled draws.

Revision ID: 0038_kasper_fast_formats
Revises: 0037_jackpot_only_telegram
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038_kasper_fast_formats"
down_revision: str | Sequence[str] | None = "0037_jackpot_only_telegram"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Draw snapshots are immutable rule contracts. Freeze the old format before
    # switching the lottery defaults used to create future draws.
    op.execute(
        sa.text(
            """
            UPDATE draws AS draw
            SET configuration_snapshot = COALESCE(
                draw.configuration_snapshot, '{}'::jsonb
            ) || jsonb_build_object(
                'ruleset_code', lottery.ruleset_code,
                'numbers_to_pick', lottery.numbers_to_pick,
                'max_number', lottery.max_number
            )
            FROM lotteries AS lottery
            WHERE lottery.id = draw.lottery_id
              AND lottery.code IN ('flash', 'pulse')
              AND draw.status = 'SCHEDULED'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE lotteries
            SET ruleset_code = 'fast_3_16', numbers_to_pick = 3, max_number = 16
            WHERE code = 'flash'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE lotteries
            SET ruleset_code = 'pulse_2_10_2_5', numbers_to_pick = 4,
                max_number = 15
            WHERE code = 'pulse'
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    new_draws = connection.scalar(
        sa.text(
            """
            SELECT count(*) FROM draws
            WHERE configuration_snapshot ->> 'ruleset_code'
                IN ('fast_3_16', 'pulse_2_10_2_5')
            """
        )
    )
    if new_draws:
        raise RuntimeError("New Kasper Fast draws prevent safe downgrade.")
    op.execute(
        sa.text(
            """
            UPDATE lotteries
            SET ruleset_code = 'fast_3_15', numbers_to_pick = 3, max_number = 15
            WHERE code = 'flash'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE lotteries
            SET ruleset_code = 'pulse_2_10_1_5', numbers_to_pick = 3,
                max_number = 15
            WHERE code = 'pulse'
            """
        )
    )
