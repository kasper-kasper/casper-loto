"""Add the FLASH and SHADOW fast lotteries.

Revision ID: 0024_fast_lotteries
Revises: 0023_kasper_constraints
Create Date: 2026-09-01
"""

import json
from collections.abc import Sequence
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0024_fast_lotteries"
down_revision: str | Sequence[str] | None = "0023_kasper_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BASE_JACKPOT = 888_888
LOTTERIES = (
    {
        "id": UUID("10000000-0000-0000-0000-000000000815"),
        "jackpot_id": UUID("10000000-0000-0000-0000-000000001815"),
        "distribution_id": UUID("10000000-0000-0000-0000-000000002815"),
        "reserve_id": UUID("10000000-0000-0000-0000-000000003815"),
        "code": "flash",
        "name": "FLASH",
        "anchor_time": "00:00",
    },
    {
        "id": UUID("10000000-0000-0000-0000-000000000915"),
        "jackpot_id": UUID("10000000-0000-0000-0000-000000001915"),
        "distribution_id": UUID("10000000-0000-0000-0000-000000002915"),
        "reserve_id": UUID("10000000-0000-0000-0000-000000003915"),
        "code": "shadow",
        "name": "SHADOW",
        "anchor_time": "00:10",
    },
)


def upgrade() -> None:
    connection = op.get_bind()
    op.execute(
        """
        DO $$
        DECLARE current_name text;
        BEGIN
            SELECT conname INTO current_name
            FROM pg_constraint
            WHERE conrelid = 'user_notifications'::regclass
              AND contype = 'c'
              AND pg_get_constraintdef(oid) LIKE '%JACKPOT_NEWS%';
            IF current_name IS NOT NULL THEN
                EXECUTE format(
                    'ALTER TABLE user_notifications DROP CONSTRAINT %I',
                    current_name
                );
            END IF;
        END $$;
        """
    )
    op.create_check_constraint(
        "in_app_notification_type",
        "user_notifications",
        "type IN ('WIN', 'DRAW_RESULT', 'DRAW_INVITATION', 'JACKPOT_NEWS')",
    )
    for item in LOTTERIES:
        schedule = {
            "type": "interval",
            "interval_minutes": 20,
            "anchor_time": item["anchor_time"],
            "future_draw_count": 2,
            "category": "fast",
            "live_enabled": False,
            "telegram_notifications": False,
            "owner_auto_play": False,
        }
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
                    :id, :code, :name, 'DAILY', 'fast_3_15', 3, 15, 888,
                    'Europe/Moscow', CAST(:schedule AS jsonb), 1, 100, 500,
                    true, 1, 1
                )
                """
            ),
            {**item, "schedule": json.dumps(schedule)},
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO jackpot_accounts
                    (id, lottery_id, balance, base_amount, version)
                VALUES (:jackpot_id, :id, :amount, :amount, 1)
                """
            ),
            {**item, "amount": BASE_JACKPOT},
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO distribution_funds (id, lottery_id, balance, version)
                VALUES (:distribution_id, :id, 0, 1)
                """
            ),
            item,
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO lottery_reserves (id, lottery_id, balance, version)
                VALUES (:reserve_id, :id, 0, 1)
                """
            ),
            item,
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO ledger_transactions (
                    id, operation_id, idempotency_key, account_kind, account_id,
                    type, amount, balance_before, balance_after, lottery_id,
                    metadata
                ) VALUES (
                    :transaction_id, :operation_id, :key, 'JACKPOT',
                    :jackpot_id, 'SYSTEM_ADJUSTMENT', :amount, 0, :amount,
                    :id, CAST(:metadata AS jsonb)
                )
                """
            ),
            {
                **item,
                "transaction_id": uuid4(),
                "operation_id": uuid4(),
                "key": f"migration:0024:{item['code']}:jackpot",
                "amount": BASE_JACKPOT,
                "metadata": json.dumps(
                    {"reason": f"Стартовый джекпот {item['name']}"},
                    ensure_ascii=False,
                ),
            },
        )


def downgrade() -> None:
    connection = op.get_bind()
    for item in reversed(LOTTERIES):
        has_history = connection.execute(
            sa.text(
                "SELECT EXISTS(SELECT 1 FROM draws WHERE lottery_id=:id) "
                "OR EXISTS(SELECT 1 FROM tickets WHERE lottery_id=:id)"
            ),
            {"id": item["id"]},
        ).scalar()
        if has_history:
            raise RuntimeError("Cannot remove a lottery after business history exists.")
        connection.execute(
            sa.text("DELETE FROM ledger_transactions WHERE lottery_id=:id"),
            {"id": item["id"]},
        )
        for table in ("lottery_reserves", "distribution_funds", "jackpot_accounts"):
            connection.execute(
                sa.text(f"DELETE FROM {table} WHERE lottery_id=:id"),
                {"id": item["id"]},
            )
        connection.execute(
            sa.text("DELETE FROM lotteries WHERE id=:id"), {"id": item["id"]}
        )
    op.execute(
        """
        DO $$
        DECLARE current_name text;
        BEGIN
            SELECT conname INTO current_name
            FROM pg_constraint
            WHERE conrelid = 'user_notifications'::regclass
              AND contype = 'c'
              AND pg_get_constraintdef(oid) LIKE '%DRAW_RESULT%';
            IF current_name IS NOT NULL THEN
                EXECUTE format(
                    'ALTER TABLE user_notifications DROP CONSTRAINT %I',
                    current_name
                );
            END IF;
        END $$;
        """
    )
    op.create_check_constraint(
        "in_app_notification_type",
        "user_notifications",
        "type IN ('WIN', 'DRAW_INVITATION', 'JACKPOT_NEWS')",
    )
