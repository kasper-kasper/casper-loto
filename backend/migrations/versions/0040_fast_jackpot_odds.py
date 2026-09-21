"""Reduce FLASH and PULSE jackpot frequency for future draws.

Revision ID: 0040_fast_jackpot_odds
Revises: 0039_interesting_facts
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0040_fast_jackpot_odds"
down_revision: str | Sequence[str] | None = "0039_interesting_facts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A draw snapshot is its immutable rule contract. Preserve the format of
    # every already scheduled draw before changing defaults for future draws.
    op.execute(
        sa.text(
            """
            UPDATE draws AS draw
            SET configuration_snapshot = jsonb_build_object(
                'ruleset_code', lottery.ruleset_code,
                'numbers_to_pick', lottery.numbers_to_pick,
                'max_number', lottery.max_number
            ) || COALESCE(draw.configuration_snapshot, '{}'::jsonb)
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
            SET ruleset_code = 'fast_3_20', numbers_to_pick = 3, max_number = 20
            WHERE code = 'flash'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE lotteries
            SET ruleset_code = 'pulse_2_12_2_6', numbers_to_pick = 4,
                max_number = 18
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
                IN ('fast_3_20', 'pulse_2_12_2_6')
            """
        )
    )
    if new_draws:
        raise RuntimeError("New Kasper Fast draws prevent safe downgrade.")
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
