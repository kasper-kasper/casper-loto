"""Add PULSE and move Fast lotteries to a three-minute rotation.

Revision ID: 0028_pulse_fast
Revises: 0027_kasper_grand
Create Date: 2026-09-04
"""

import json
from collections.abc import Sequence
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0028_pulse_fast"
down_revision: str | Sequence[str] | None = "0027_kasper_grand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LOTTERY_ID = UUID("10000000-0000-0000-0000-000000001015")
JACKPOT_ID = UUID("10000000-0000-0000-0000-000000001115")
DISTRIBUTION_ID = UUID("10000000-0000-0000-0000-000000001215")
RESERVE_ID = UUID("10000000-0000-0000-0000-000000001315")
BASE_JACKPOT = 1_234_567
TICKET_PRICE = 1_234


def _schedule(anchor_time: str) -> str:
    return json.dumps(
        {
            "type": "interval",
            "interval_minutes": 9,
            "anchor_time": anchor_time,
            "future_draw_count": 2,
            "category": "fast",
            "live_enabled": True,
        }
    )


def upgrade() -> None:
    connection = op.get_bind()
    for code, anchor_time in (("flash", "00:00"), ("shadow", "00:03")):
        connection.execute(
            sa.text(
                """
                UPDATE lotteries
                SET schedule = schedule || CAST(:schedule AS jsonb),
                    sales_cutoff_minutes = 1
                WHERE code = :code
                """
            ),
            {"code": code, "schedule": _schedule(anchor_time)},
        )

    schedule = _schedule("00:06")
    connection.execute(
        sa.text(
            """
            INSERT INTO lotteries (
                id, code, name, kind, ruleset_code, numbers_to_pick,
                max_number, ticket_price, timezone, schedule,
                sales_cutoff_minutes, max_tickets_per_purchase,
                max_tickets_per_user_per_draw, is_active,
                next_draw_number, next_ticket_number
            ) VALUES (
                :id, 'pulse', 'PULSE', 'DAILY', 'pulse_2_10_1_5', 3, 15,
                :ticket_price, 'Europe/Moscow', CAST(:schedule AS jsonb),
                1, 100, 500, true, 1, 1
            )
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name,
                ruleset_code = EXCLUDED.ruleset_code,
                numbers_to_pick = EXCLUDED.numbers_to_pick,
                max_number = EXCLUDED.max_number,
                schedule = EXCLUDED.schedule,
                sales_cutoff_minutes = EXCLUDED.sales_cutoff_minutes,
                is_active = true
            """
        ),
        {
            "id": LOTTERY_ID,
            "ticket_price": TICKET_PRICE,
            "schedule": schedule,
        },
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO jackpot_accounts
                (id, lottery_id, balance, base_amount, version)
            VALUES (:id, :lottery_id, :amount, :amount, 1)
            ON CONFLICT (lottery_id) DO NOTHING
            """
        ),
        {"id": JACKPOT_ID, "lottery_id": LOTTERY_ID, "amount": BASE_JACKPOT},
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO distribution_funds (id, lottery_id, balance, version)
            VALUES (:id, :lottery_id, 0, 1)
            ON CONFLICT (lottery_id) DO NOTHING
            """
        ),
        {"id": DISTRIBUTION_ID, "lottery_id": LOTTERY_ID},
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO lottery_reserves (id, lottery_id, balance, version)
            VALUES (:id, :lottery_id, 0, 1)
            ON CONFLICT (lottery_id) DO NOTHING
            """
        ),
        {"id": RESERVE_ID, "lottery_id": LOTTERY_ID},
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO ledger_transactions (
                id, operation_id, idempotency_key, account_kind, account_id,
                type, amount, balance_before, balance_after, lottery_id, metadata
            ) VALUES (
                :id, :operation_id, 'migration:0028:pulse:jackpot', 'JACKPOT',
                :account_id, 'SYSTEM_ADJUSTMENT', :amount, 0, :amount,
                :lottery_id, CAST(:metadata AS jsonb)
            )
            ON CONFLICT (idempotency_key) DO NOTHING
            """
        ),
        {
            "id": uuid4(),
            "operation_id": uuid4(),
            "account_id": JACKPOT_ID,
            "amount": BASE_JACKPOT,
            "lottery_id": LOTTERY_ID,
            "metadata": json.dumps(
                {"reason": "Стартовый джекпот PULSE"}, ensure_ascii=False
            ),
        },
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_history = connection.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM draws WHERE lottery_id=:lottery_id) "
            "OR EXISTS(SELECT 1 FROM tickets WHERE lottery_id=:lottery_id)"
        ),
        {"lottery_id": LOTTERY_ID},
    ).scalar()
    if has_history:
        raise RuntimeError("Cannot remove PULSE after business history exists.")
    connection.execute(
        sa.text("DELETE FROM ledger_transactions WHERE lottery_id=:lottery_id"),
        {"lottery_id": LOTTERY_ID},
    )
    for table in ("lottery_reserves", "distribution_funds", "jackpot_accounts"):
        connection.execute(
            sa.text(f"DELETE FROM {table} WHERE lottery_id=:lottery_id"),
            {"lottery_id": LOTTERY_ID},
        )
    connection.execute(
        sa.text("DELETE FROM lotteries WHERE id=:lottery_id"),
        {"lottery_id": LOTTERY_ID},
    )
    for code, anchor_time in (("flash", "00:00"), ("shadow", "00:10")):
        connection.execute(
            sa.text(
                """
                UPDATE lotteries
                SET schedule = schedule || CAST(:schedule AS jsonb)
                WHERE code = :code
                """
            ),
            {
                "code": code,
                "schedule": json.dumps(
                    {
                        "type": "interval",
                        "interval_minutes": 20,
                        "anchor_time": anchor_time,
                        "future_draw_count": 2,
                    }
                ),
            },
        )
