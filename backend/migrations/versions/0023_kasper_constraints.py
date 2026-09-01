"""Normalize Kasper Fund check-constraint names.

Revision ID: 0023_kasper_constraints
Revises: 0022_kasper_fund
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_kasper_constraints"
down_revision: str | Sequence[str] | None = "0022_kasper_fund"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            DO $$
            DECLARE item record;
            DECLARE current_name text;
            BEGIN
                FOR item IN
                    SELECT * FROM (VALUES
                        ('kasper_fund_accounts', 'balance >= 0',
                         'ck_kasper_fund_accounts_balance_nonnegative'),
                        ('jackpot_win_events', 'jackpot_amount > 0',
                         'ck_jackpot_win_events_amount_positive'),
                        ('jackpot_win_events', 'winner_ticket_count > 0',
                         'ck_jackpot_win_events_ticket_count_positive'),
                        ('jackpot_win_events', 'winner_user_count > 0',
                         'ck_jackpot_win_events_user_count_positive')
                    ) AS values_to_apply(table_name, needle, desired)
                LOOP
                    SELECT conname INTO current_name
                    FROM pg_constraint
                    WHERE conrelid = to_regclass(item.table_name)
                      AND contype = 'c'
                      AND pg_get_constraintdef(oid) LIKE '%' || item.needle || '%';
                    IF current_name IS NOT NULL AND current_name <> item.desired THEN
                        EXECUTE format(
                            'ALTER TABLE %I RENAME CONSTRAINT %I TO %I',
                            item.table_name, current_name, item.desired
                        );
                    END IF;
                END LOOP;
            END $$;
            """
        )
    )


def downgrade() -> None:
    # Constraint names do not change behavior or data.
    return
