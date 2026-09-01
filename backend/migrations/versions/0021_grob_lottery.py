"""Add the GROB 3 of 16 daily lottery.

Revision ID: 0021_grob_lottery
Revises: 0020_september_numbering
Create Date: 2026-09-01
"""

import json
from collections.abc import Sequence
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0021_grob_lottery"
down_revision: str | Sequence[str] | None = "0020_september_numbering"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LOTTERY_ID = UUID("10000000-0000-0000-0000-000000000916")
JACKPOT_ID = UUID("10000000-0000-0000-0000-000000001916")
DISTRIBUTION_ID = UUID("10000000-0000-0000-0000-000000002916")
RESERVE_ID = UUID("10000000-0000-0000-0000-000000003916")
BASE_JACKPOT = 6_666_666
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
    connection.execute(
        sa.text(
            """
            INSERT INTO lotteries (
                id, code, name, kind, ruleset_code, numbers_to_pick, max_number,
                ticket_price, timezone, schedule, sales_cutoff_minutes,
                max_tickets_per_purchase, max_tickets_per_user_per_draw,
                is_active, next_draw_number, next_ticket_number
            ) VALUES (
                :id, 'grob', 'ГРОБ', 'DAILY', 'grob_3_16', 3, 16,
                6666, 'Europe/Moscow', CAST(:schedule AS jsonb), 2,
                1000, 5000, true, 1, 1
            )
            """
        ),
        {
            "id": LOTTERY_ID,
            "schedule": json.dumps({"slots": ["06:06", "23:06"]}),
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
        {"id": JACKPOT_ID, "lottery_id": LOTTERY_ID, "amount": BASE_JACKPOT},
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
        amount=BASE_JACKPOT,
        key="migration:0021:grob:jackpot",
        reason="Базовый джекпот лотереи ГРОБ утверждён владельцем",
    )
    _credit(
        connection,
        account_id=RESERVE_ID,
        account_kind="LOTTERY_RESERVE",
        amount=INITIAL_RESERVE,
        key="migration:0021:grob:reserve",
        reason="Стартовый резерв по модели ежедневных лотерей",
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_history = connection.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM draws WHERE lottery_id=:id) "
            "OR EXISTS(SELECT 1 FROM tickets WHERE lottery_id=:id)"
        ),
        {"id": LOTTERY_ID},
    ).scalar()
    if has_history:
        raise RuntimeError("Cannot remove a lottery after business history exists.")
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
