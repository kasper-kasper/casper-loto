"""Unify new lottery funding through the Kasper Fund.

Revision ID: 0022_kasper_fund
Revises: 0021_grob_lottery
Create Date: 2026-09-01
"""

import json
from collections.abc import Sequence
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022_kasper_fund"
down_revision: str | Sequence[str] | None = "0021_grob_lottery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FUND_ID = UUID("4b415350-4552-4655-4e44-000000000001")
TARGET_BALANCE = 1_000_000_000_000_000


def _ledger(
    connection: sa.Connection,
    *,
    operation_id: UUID,
    key: str,
    kind: str,
    account_id: UUID,
    before: int,
    after: int,
    lottery_id: UUID | None,
    reason: str,
) -> None:
    if before == after:
        return
    connection.execute(
        sa.text(
            """
            INSERT INTO ledger_transactions (
                id, operation_id, idempotency_key, account_kind, account_id,
                type, amount, balance_before, balance_after, lottery_id, metadata
            ) VALUES (
                :id, :operation_id, :key, :kind, :account_id,
                'SYSTEM_ADJUSTMENT', :amount, :before, :after, :lottery_id,
                CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "id": uuid4(),
            "operation_id": operation_id,
            "key": key,
            "kind": kind,
            "account_id": account_id,
            "amount": after - before,
            "before": before,
            "after": after,
            "lottery_id": lottery_id,
            "metadata": json.dumps({"reason": reason}, ensure_ascii=False),
        },
    )


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DO $$
            DECLARE current_name text;
            BEGIN
                SELECT conname INTO current_name
                FROM pg_constraint
                WHERE conrelid = 'ledger_transactions'::regclass
                  AND contype = 'c'
                  AND pg_get_constraintdef(oid) LIKE '%account_kind%';
                IF current_name IS NOT NULL THEN
                    EXECUTE format(
                        'ALTER TABLE ledger_transactions DROP CONSTRAINT %I',
                        current_name
                    );
                END IF;
            END $$;
            """
        )
    )
    op.create_check_constraint(
        "ledger_account_kind",
        "ledger_transactions",
        "account_kind IN ('USER_BALANCE', 'JACKPOT', 'DISTRIBUTION_FUND', "
        "'LOTTERY_RESERVE', 'KASPER_FUND')",
    )
    connection.execute(
        sa.text(
            """
            DO $$
            DECLARE current_name text;
            BEGIN
                SELECT conname INTO current_name
                FROM pg_constraint
                WHERE conrelid = 'user_notifications'::regclass
                  AND contype = 'c'
                  AND pg_get_constraintdef(oid) LIKE '%DRAW_INVITATION%';
                IF current_name IS NOT NULL THEN
                    EXECUTE format(
                        'ALTER TABLE user_notifications DROP CONSTRAINT %I',
                        current_name
                    );
                END IF;
            END $$;
            """
        )
    )
    op.create_check_constraint(
        "in_app_notification_type",
        "user_notifications",
        "type IN ('WIN', 'DRAW_INVITATION', 'JACKPOT_NEWS')",
    )
    op.add_column(
        "draws",
        sa.Column(
            "kasper_fund_used", sa.BigInteger(), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "draws",
        sa.Column(
            "configuration_snapshot",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "kasper_fund_used_nonnegative", "draws", "kasper_fund_used >= 0"
    )
    op.create_table(
        "kasper_fund_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("balance", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "balance >= 0", name="ck_kasper_fund_accounts_balance_nonnegative"
        ),
    )
    op.create_table(
        "jackpot_win_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "draw_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True
        ),
        sa.Column("lottery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jackpot_amount", sa.BigInteger(), nullable=False),
        sa.Column("winner_ticket_count", sa.Integer(), nullable=False),
        sa.Column("winner_user_count", sa.Integer(), nullable=False),
        sa.Column("base_jackpot_after", sa.BigInteger(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["draw_id"], ["draws.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lottery_id"], ["lotteries.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "jackpot_amount > 0", name="ck_jackpot_win_events_amount_positive"
        ),
        sa.CheckConstraint(
            "winner_ticket_count > 0",
            name="ck_jackpot_win_events_ticket_count_positive",
        ),
        sa.CheckConstraint(
            "winner_user_count > 0", name="ck_jackpot_win_events_user_count_positive"
        ),
    )
    op.create_index("ix_jackpot_win_occurred", "jackpot_win_events", ["occurred_at"])

    connection.execute(
        sa.text(
            """
            UPDATE draws AS d
            SET configuration_snapshot = jsonb_build_object(
                'ruleset_code', l.ruleset_code,
                'ticket_price', l.ticket_price,
                'numbers_to_pick', l.numbers_to_pick,
                'max_number', l.max_number,
                'base_jackpot', j.base_amount
            )
            FROM lotteries AS l
            JOIN jackpot_accounts AS j ON j.lottery_id = l.id
            WHERE d.lottery_id = l.id
            """
        )
    )
    legacy_rows = (
        connection.execute(
            sa.text(
                """
            SELECT 'DISTRIBUTION_FUND' AS kind, id, lottery_id, balance
            FROM distribution_funds WHERE balance > 0
            UNION ALL
            SELECT 'LOTTERY_RESERVE', id, lottery_id, balance
            FROM lottery_reserves WHERE balance > 0
            """
            )
        )
        .mappings()
        .all()
    )
    legacy_total = sum(int(row["balance"]) for row in legacy_rows)
    connection.execute(
        sa.text(
            "INSERT INTO kasper_fund_accounts (id, balance, version) "
            "VALUES (:id, :balance, 1)"
        ),
        {"id": FUND_ID, "balance": max(TARGET_BALANCE, legacy_total)},
    )
    for row in legacy_rows:
        operation_id = uuid4()
        amount = int(row["balance"])
        _ledger(
            connection,
            operation_id=operation_id,
            key=f"kasper-fund:migrate:{row['kind']}:{row['id']}:debit",
            kind=str(row["kind"]),
            account_id=row["id"],
            before=amount,
            after=0,
            lottery_id=row["lottery_id"],
            reason="Перенос остатка в единый Фонд Каспера",
        )
        table = (
            "distribution_funds"
            if row["kind"] == "DISTRIBUTION_FUND"
            else "lottery_reserves"
        )
        connection.execute(
            sa.text(
                f"UPDATE {table} SET balance = 0, version = version + 1 WHERE id = :id"
            ),
            {"id": row["id"]},
        )
    fund_balance = max(TARGET_BALANCE, legacy_total)
    _ledger(
        connection,
        operation_id=uuid4(),
        key="kasper-fund:initial",
        kind="KASPER_FUND",
        account_id=FUND_ID,
        before=0,
        after=fund_balance,
        lottery_id=None,
        reason="Начальный баланс единого Фонда Каспера",
    )


def downgrade() -> None:
    raise RuntimeError(
        "The Kasper Fund migration preserves immutable financial history."
    )
