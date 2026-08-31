"""Unify named Daily slots under one shared lottery and fund set.

Revision ID: 0007_unified_daily_lottery
Revises: 0006_lottery_lineup
Create Date: 2026-08-20
"""

import json
from collections.abc import Sequence
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0007_unified_daily_lottery"
down_revision: str | Sequence[str] | None = "0006_lottery_lineup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_CODES = ("pss", "khan", "pll")
TARGET_JACKPOT = 24_000_000


def _ledger_entry(
    connection: sa.Connection,
    *,
    operation_id: UUID,
    key: str,
    account_kind: str,
    account_id: UUID,
    amount: int,
    before: int,
    after: int,
    lottery_id: UUID,
    reason: str,
) -> None:
    if amount == 0:
        return
    connection.execute(
        sa.text(
            """
            INSERT INTO ledger_transactions (
                id, operation_id, idempotency_key, account_kind, account_id,
                type, amount, balance_before, balance_after, lottery_id, metadata
            ) VALUES (
                :id, :operation_id, :key, :account_kind, :account_id,
                'SYSTEM_ADJUSTMENT', :amount, :before, :after, :lottery_id,
                CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "id": uuid4(),
            "operation_id": operation_id,
            "key": key,
            "account_kind": account_kind,
            "account_id": account_id,
            "amount": amount,
            "before": before,
            "after": after,
            "lottery_id": lottery_id,
            "metadata": json.dumps({"reason": reason}, ensure_ascii=False),
        },
    )


def _move_account(
    connection: sa.Connection,
    *,
    table: str,
    account_kind: str,
    source_lottery_id: UUID,
    target_lottery_id: UUID,
    source_code: str,
) -> None:
    source = (
        connection.execute(
            sa.text(f"SELECT id, balance FROM {table} WHERE lottery_id=:lottery_id"),
            {"lottery_id": source_lottery_id},
        )
        .mappings()
        .one()
    )
    target = (
        connection.execute(
            sa.text(
                f"SELECT id, balance FROM {table} "
                "WHERE lottery_id=:lottery_id FOR UPDATE"
            ),
            {"lottery_id": target_lottery_id},
        )
        .mappings()
        .one()
    )
    amount = int(source["balance"])
    if amount == 0:
        return
    operation_id = uuid4()
    reason = f"Объединение {source_code} в единую ежедневную лотерею"
    _ledger_entry(
        connection,
        operation_id=operation_id,
        key=f"migration:0007:{source_code}:{account_kind}:debit",
        account_kind=account_kind,
        account_id=source["id"],
        amount=-amount,
        before=amount,
        after=0,
        lottery_id=source_lottery_id,
        reason=reason,
    )
    target_before = int(target["balance"])
    _ledger_entry(
        connection,
        operation_id=operation_id,
        key=f"migration:0007:{source_code}:{account_kind}:credit",
        account_kind=account_kind,
        account_id=target["id"],
        amount=amount,
        before=target_before,
        after=target_before + amount,
        lottery_id=target_lottery_id,
        reason=reason,
    )
    connection.execute(
        sa.text(f"UPDATE {table} SET balance=0, version=version+1 WHERE id=:id"),
        {"id": source["id"]},
    )
    connection.execute(
        sa.text(f"UPDATE {table} SET balance=:balance, version=version+1 WHERE id=:id"),
        {"id": target["id"], "balance": target_before + amount},
    )


def upgrade() -> None:
    connection = op.get_bind()
    daily_id = connection.execute(
        sa.text("SELECT id FROM lotteries WHERE code='daily' FOR UPDATE")
    ).scalar_one()

    # Only empty prepared draws are transitional state, not business history.
    # A non-empty draw aborts the migration instead of moving purchased tickets.
    live_ticket_count = connection.execute(
        sa.text(
            """
            SELECT count(*) FROM tickets t
            JOIN lotteries l ON l.id=t.lottery_id
            WHERE l.code IN ('pss', 'khan', 'pll') AND t.status='PURCHASED'
            """
        )
    ).scalar_one()
    if live_ticket_count:
        raise RuntimeError(
            "Cannot unify Daily lotteries while legacy tickets are still active."
        )
    connection.execute(
        sa.text(
            """
            DELETE FROM draws d USING lotteries l
            WHERE d.lottery_id=l.id
              AND l.code IN ('pss', 'khan', 'pll')
              AND d.status='SCHEDULED'
              AND NOT EXISTS (SELECT 1 FROM tickets t WHERE t.draw_id=d.id)
            """
        )
    )

    accounts = (
        ("jackpot_accounts", "JACKPOT"),
        ("distribution_funds", "DISTRIBUTION_FUND"),
        ("lottery_reserves", "LOTTERY_RESERVE"),
    )
    for source_code in LEGACY_CODES:
        source_id = connection.execute(
            sa.text("SELECT id FROM lotteries WHERE code=:code FOR UPDATE"),
            {"code": source_code},
        ).scalar_one()
        for table, account_kind in accounts:
            _move_account(
                connection,
                table=table,
                account_kind=account_kind,
                source_lottery_id=source_id,
                target_lottery_id=daily_id,
                source_code=source_code,
            )

    jackpot = (
        connection.execute(
            sa.text(
                "SELECT id, balance FROM jackpot_accounts "
                "WHERE lottery_id=:lottery_id FOR UPDATE"
            ),
            {"lottery_id": daily_id},
        )
        .mappings()
        .one()
    )
    before = int(jackpot["balance"])
    adjustment = TARGET_JACKPOT - before
    _ledger_entry(
        connection,
        operation_id=uuid4(),
        key="migration:0007:daily:jackpot:owner-target",
        account_kind="JACKPOT",
        account_id=jackpot["id"],
        amount=adjustment,
        before=before,
        after=TARGET_JACKPOT,
        lottery_id=daily_id,
        reason="Единый ежедневный джекпот утверждён владельцем",
    )
    connection.execute(
        sa.text(
            "UPDATE jackpot_accounts SET balance=:target, base_amount=:target, "
            "version=version+1 WHERE id=:id"
        ),
        {"id": jackpot["id"], "target": TARGET_JACKPOT},
    )
    connection.execute(
        sa.text(
            """
            UPDATE lotteries SET
                name='Ежедневная лотерея', ticket_price=24000,
                schedule='{"slots":["02:22","12:00","18:00"]}'::jsonb,
                sales_cutoff_minutes=2, is_active=true
            WHERE code='daily'
            """
        )
    )
    connection.execute(
        sa.text(
            "UPDATE lotteries SET is_active=false WHERE code IN ('pss', 'khan', 'pll')"
        )
    )


def downgrade() -> None:
    raise RuntimeError(
        "Unified Daily funds cannot be split without an explicit owner allocation."
    )
