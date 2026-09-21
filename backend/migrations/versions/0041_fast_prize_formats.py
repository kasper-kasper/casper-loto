"""Introduce jackpot-only FLASH, cipher PULSE and five-digit CODE.

Revision ID: 0041_fast_prize_formats
Revises: 0040_fast_jackpot_odds
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0041_fast_prize_formats"
down_revision: str | Sequence[str] | None = "0040_fast_jackpot_odds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
              AND lottery.code IN ('flash', 'pulse', 'shadow')
              AND draw.status = 'SCHEDULED'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE lotteries SET
                ruleset_code = CASE code
                    WHEN 'flash' THEN 'fast_5_20_jackpot_only'
                    WHEN 'pulse' THEN 'pulse_2_12_2_6_cipher_199'
                    WHEN 'shadow' THEN 'code_5_digits'
                END,
                numbers_to_pick = CASE code
                    WHEN 'flash' THEN 5
                    WHEN 'pulse' THEN 5
                    WHEN 'shadow' THEN 5
                END,
                max_number = CASE code
                    WHEN 'flash' THEN 20
                    WHEN 'pulse' THEN 18
                    WHEN 'shadow' THEN 9
                END,
                updated_at = now()
            WHERE code IN ('flash', 'pulse', 'shadow')
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    new_draws = connection.scalar(
        sa.text(
            """
            SELECT count(*) FROM draws
            WHERE configuration_snapshot ->> 'ruleset_code' IN (
                'fast_5_20_jackpot_only',
                'pulse_2_12_2_6_cipher_199',
                'code_5_digits'
            )
            """
        )
    )
    if new_draws:
        raise RuntimeError("New Kasper Fast draws prevent safe downgrade.")
    op.execute(
        sa.text(
            """
            UPDATE lotteries SET
                ruleset_code = CASE code
                    WHEN 'flash' THEN 'fast_3_20'
                    WHEN 'pulse' THEN 'pulse_2_12_2_6'
                    WHEN 'shadow' THEN 'code_4_digits'
                END,
                numbers_to_pick = CASE code
                    WHEN 'flash' THEN 3
                    WHEN 'pulse' THEN 4
                    WHEN 'shadow' THEN 4
                END,
                max_number = CASE code
                    WHEN 'flash' THEN 20
                    WHEN 'pulse' THEN 18
                    WHEN 'shadow' THEN 9
                END,
                updated_at = now()
            WHERE code IN ('flash', 'pulse', 'shadow')
            """
        )
    )
