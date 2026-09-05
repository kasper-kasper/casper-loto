"""Add Kasper Bingo inventory and ledger-funded starting jackpot.

Revision ID: 0033_kasper_bingo
Revises: 0032_classic_prizes
Create Date: 2026-09-04
"""

import json
from collections.abc import Sequence
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0033_kasper_bingo"
down_revision: str | Sequence[str] | None = "0032_classic_prizes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LOTTERY_ID = UUID("10000000-0000-0000-0000-000000001016")
JACKPOT_ID = UUID("10000000-0000-0000-0000-000000001116")
DISTRIBUTION_ID = UUID("10000000-0000-0000-0000-000000001216")
RESERVE_ID = UUID("10000000-0000-0000-0000-000000001316")
BASE_JACKPOT = 10_000_000_000
TICKET_PRICE = 50_000


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("bingo_result", sa.dialects.postgresql.JSONB(), nullable=True),
    )
    op.create_table(
        "bingo_pool_tickets",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "draw_id",
            sa.UUID(),
            sa.ForeignKey("draws.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("public_number", sa.BigInteger(), nullable=False, unique=True),
        sa.Column(
            "numbers", sa.dialects.postgresql.ARRAY(sa.Integer()), nullable=False
        ),
        sa.Column(
            "ticket_id",
            sa.UUID(),
            sa.ForeignKey("tickets.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.UniqueConstraint("draw_id", "public_number", name="uq_bingo_pool_serial"),
        sa.CheckConstraint("cardinality(numbers) = 12", name="bingo_twelve_numbers"),
    )
    op.create_index(
        "ix_bingo_pool_free", "bingo_pool_tickets", ["draw_id", "ticket_id"]
    )
    connection = op.get_bind()
    schedule = json.dumps({"slots": ["22:00"], "future_draw_count": 1})
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
                :id, 'bingo', 'Kasper Bingo', 'DAILY', 'bingo_12_60', 12, 60,
                :ticket_price, 'Europe/Moscow', CAST(:schedule AS jsonb),
                2, 50, 50, true, 1, 1
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
    fund_id = UUID("4b415350-4552-4655-4e44-000000000001")
    fund_before = connection.execute(
        sa.text("SELECT balance FROM kasper_fund_accounts WHERE id=:id FOR UPDATE"),
        {"id": fund_id},
    ).scalar_one()
    if fund_before < BASE_JACKPOT:
        raise RuntimeError("Kasper Fund cannot fund the initial Bingo jackpot.")
    operation_id = uuid4()
    connection.execute(
        sa.text(
            "UPDATE kasper_fund_accounts SET balance=balance-:amount, "
            "version=version+1 WHERE id=:id"
        ),
        {"id": fund_id, "amount": BASE_JACKPOT},
    )
    connection.execute(
        sa.text("""
        INSERT INTO ledger_transactions (id, operation_id, idempotency_key,
            account_kind,
            account_id, type, amount, balance_before, balance_after,
            lottery_id, metadata)
        VALUES (:id, :operation, 'migration:0033:bingo:fund', 'KASPER_FUND', :fund,
            'SYSTEM_ADJUSTMENT', :amount, :before, :after, :lottery, '{}')
    """),
        {
            "id": uuid4(),
            "operation": operation_id,
            "fund": fund_id,
            "amount": -BASE_JACKPOT,
            "before": fund_before,
            "after": fund_before - BASE_JACKPOT,
            "lottery": LOTTERY_ID,
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
                :id, :operation_id, 'migration:0033:bingo:jackpot', 'JACKPOT',
                :account_id, 'SYSTEM_ADJUSTMENT', :amount, 0, :amount,
                :lottery_id, CAST(:metadata AS jsonb)
            )
            ON CONFLICT (idempotency_key) DO NOTHING
            """
        ),
        {
            "id": uuid4(),
            "operation_id": operation_id,
            "account_id": JACKPOT_ID,
            "amount": BASE_JACKPOT,
            "lottery_id": LOTTERY_ID,
            "metadata": json.dumps(
                {"reason": "Стартовый джекпот Kasper Bingo"}, ensure_ascii=False
            ),
        },
    )


def downgrade() -> None:
    raise RuntimeError("Bingo financial history is immutable; use a forward migration.")
