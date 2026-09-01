"""Add the fixed-prize 3 СЕНТЯБРЯ daily lottery.

Revision ID: 0019_september_lottery
Revises: 0018_lottery_rulesets
Create Date: 2026-09-01
"""

import json
from collections.abc import Sequence
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0019_september_lottery"
down_revision: str | Sequence[str] | None = "0018_lottery_rulesets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LOTTERY_ID = UUID("10000000-0000-0000-0000-000000000903")
JACKPOT_ID = UUID("10000000-0000-0000-0000-000000001903")
DISTRIBUTION_ID = UUID("10000000-0000-0000-0000-000000002903")
RESERVE_ID = UUID("10000000-0000-0000-0000-000000003903")
MAIN_PRIZE = 33_333_333
INITIAL_RESERVE = 1_000_000_000


def _credit(
    connection: sa.Connection,
    *,
    account_id: UUID,
    account_kind: str,
    amount: int,
    key: str,
    reason: str,
) -> None:
    connection.execute(
        sa.text(
            """
            INSERT INTO ledger_transactions (
                id, operation_id, idempotency_key, account_kind, account_id,
                type, amount, balance_before, balance_after, lottery_id, metadata
            ) VALUES (
                :id, :operation_id, :key, :kind, :account_id,
                'SYSTEM_ADJUSTMENT', :amount, 0, :amount, :lottery_id,
                CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "id": uuid4(),
            "operation_id": uuid4(),
            "key": key,
            "kind": account_kind,
            "account_id": account_id,
            "amount": amount,
            "lottery_id": LOTTERY_ID,
            "metadata": json.dumps({"reason": reason}, ensure_ascii=False),
        },
    )


def upgrade() -> None:
    connection = op.get_bind()
    next_draw = int(
        connection.execute(
            sa.text("SELECT COALESCE(MAX(next_draw_number), 1) FROM lotteries")
        ).scalar_one()
    )
    next_ticket = int(
        connection.execute(
            sa.text("SELECT COALESCE(MAX(next_ticket_number), 1) FROM lotteries")
        ).scalar_one()
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO lotteries (
                id, code, name, kind, ruleset_code, numbers_to_pick, max_number,
                ticket_price, timezone, schedule, sales_cutoff_minutes,
                max_tickets_per_purchase, max_tickets_per_user_per_draw,
                is_active, next_draw_number, next_ticket_number
            ) VALUES (
                :id, 'september', '3 СЕНТЯБРЯ', 'DAILY', 'september_3_33', 3, 33,
                333, 'Europe/Moscow', CAST(:schedule AS jsonb), 2,
                1000, 5000, true, :next_draw, :next_ticket
            )
            """
        ),
        {
            "id": LOTTERY_ID,
            "schedule": json.dumps({"slots": ["03:33", "15:33"]}),
            "next_draw": next_draw,
            "next_ticket": next_ticket,
        },
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO jackpot_accounts
                (id, lottery_id, balance, base_amount, version)
            VALUES (:id, :lottery_id, :amount, :amount, 1)
            """
        ),
        {"id": JACKPOT_ID, "lottery_id": LOTTERY_ID, "amount": MAIN_PRIZE},
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO distribution_funds (id, lottery_id, balance, version)
            VALUES (:id, :lottery_id, 0, 1)
            """
        ),
        {"id": DISTRIBUTION_ID, "lottery_id": LOTTERY_ID},
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO lottery_reserves (id, lottery_id, balance, version)
            VALUES (:id, :lottery_id, :amount, 1)
            """
        ),
        {"id": RESERVE_ID, "lottery_id": LOTTERY_ID, "amount": INITIAL_RESERVE},
    )
    _credit(
        connection,
        account_id=JACKPOT_ID,
        account_kind="JACKPOT",
        amount=MAIN_PRIZE,
        key="migration:0019:september:jackpot",
        reason="Фиксированный главный приз утверждён владельцем",
    )
    _credit(
        connection,
        account_id=RESERVE_ID,
        account_kind="LOTTERY_RESERVE",
        amount=INITIAL_RESERVE,
        key="migration:0019:september:reserve",
        reason="Стартовый резерв утверждён владельцем",
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_history = connection.execute(
        sa.text("SELECT 1 FROM draws WHERE lottery_id=:id LIMIT 1"),
        {"id": LOTTERY_ID},
    ).scalar()
    if has_history:
        raise RuntimeError("Cannot remove a lottery after draw history exists.")
    connection.execute(
        sa.text("DELETE FROM ledger_transactions WHERE lottery_id=:id"),
        {"id": LOTTERY_ID},
    )
    for table in ("lottery_reserves", "distribution_funds", "jackpot_accounts"):
        connection.execute(
            sa.text(f"DELETE FROM {table} WHERE lottery_id=:id"),
            {"id": LOTTERY_ID},
        )
    connection.execute(
        sa.text("DELETE FROM lotteries WHERE id=:id"), {"id": LOTTERY_ID}
    )
