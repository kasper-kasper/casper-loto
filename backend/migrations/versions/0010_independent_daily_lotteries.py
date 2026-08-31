"""Restore three independent Daily lotteries without rewriting business history.

Revision ID: 0010_independent_daily
Revises: 0009_favorite_combinations
Create Date: 2026-08-31
"""

import json
from collections.abc import Sequence
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0010_independent_daily"
down_revision: str | Sequence[str] | None = "0009_favorite_combinations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DAILY_CODES = (
    ("pll", "ПЛЛ-лото", "02:22"),
    ("pss", "ПСС-Лото", "12:00"),
    ("khan", "ХАН-Лото", "18:00"),
)
ACCOUNT_TABLES = (
    ("jackpot_accounts", "JACKPOT"),
    ("distribution_funds", "DISTRIBUTION_FUND"),
    ("lottery_reserves", "LOTTERY_RESERVE"),
)
OWNER_JACKPOT = 24_000_000


def _ledger(
    connection: sa.Connection,
    *,
    operation_id: UUID,
    key: str,
    kind: str,
    account_id: UUID,
    amount: int,
    before: int,
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
            "amount": amount,
            "before": before,
            "after": before + amount,
            "lottery_id": lottery_id,
            "metadata": json.dumps({"reason": reason}, ensure_ascii=False),
        },
    )


def _move_balance(
    connection: sa.Connection,
    *,
    table: str,
    kind: str,
    source_id: UUID,
    target_id: UUID,
) -> None:
    source = (
        connection.execute(
            sa.text(f"SELECT id, balance FROM {table} WHERE lottery_id=:id FOR UPDATE"),
            {"id": source_id},
        )
        .mappings()
        .one()
    )
    target = (
        connection.execute(
            sa.text(f"SELECT id, balance FROM {table} WHERE lottery_id=:id FOR UPDATE"),
            {"id": target_id},
        )
        .mappings()
        .one()
    )
    amount = int(source["balance"])
    if amount == 0:
        return
    operation_id = uuid4()
    reason = "Перенос общего Daily в независимую ПЛЛ-лото"
    _ledger(
        connection,
        operation_id=operation_id,
        key=f"migration:0010:{kind}:daily:debit",
        kind=kind,
        account_id=source["id"],
        amount=-amount,
        before=amount,
        lottery_id=source_id,
        reason=reason,
    )
    target_before = int(target["balance"])
    _ledger(
        connection,
        operation_id=operation_id,
        key=f"migration:0010:{kind}:pll:credit",
        kind=kind,
        account_id=target["id"],
        amount=amount,
        before=target_before,
        lottery_id=target_id,
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


def _set_jackpot(
    connection: sa.Connection, lottery_id: UUID, code: str, target: int
) -> None:
    account = (
        connection.execute(
            sa.text(
                "SELECT id, balance FROM jackpot_accounts "
                "WHERE lottery_id=:id FOR UPDATE"
            ),
            {"id": lottery_id},
        )
        .mappings()
        .one()
    )
    before = int(account["balance"])
    adjustment = target - before
    _ledger(
        connection,
        operation_id=uuid4(),
        key=f"migration:0010:{code}:jackpot:owner-target",
        kind="JACKPOT",
        account_id=account["id"],
        amount=adjustment,
        before=before,
        lottery_id=lottery_id,
        reason=f"Базовый джекпот {code} утверждён владельцем",
    )
    connection.execute(
        sa.text(
            "UPDATE jackpot_accounts SET balance=:target, base_amount=:target, "
            "version=version+1 WHERE id=:id"
        ),
        {"target": target, "id": account["id"]},
    )


def upgrade() -> None:
    connection = op.get_bind()
    daily = (
        connection.execute(
            sa.text(
                "SELECT id, ticket_price, next_draw_number, next_ticket_number "
                "FROM lotteries WHERE code='daily' FOR UPDATE"
            )
        )
        .mappings()
        .one()
    )
    live_tickets = connection.execute(
        sa.text(
            """
            SELECT count(*) FROM tickets t
            JOIN lotteries l ON l.id=t.lottery_id
            WHERE l.code='daily' AND t.status='PURCHASED'
            """
        )
    ).scalar_one()
    connection.execute(
        sa.text(
            """
            DELETE FROM draws d USING lotteries l
            WHERE d.lottery_id=l.id AND l.code='daily' AND d.status='SCHEDULED'
              AND NOT EXISTS (SELECT 1 FROM tickets t WHERE t.draw_id=d.id)
            """
        )
    )

    named: dict[str, UUID] = {}
    for code, name, draw_time in DAILY_CODES:
        row = (
            connection.execute(
                sa.text("SELECT id FROM lotteries WHERE code=:code FOR UPDATE"),
                {"code": code},
            )
            .mappings()
            .one()
        )
        named[code] = row["id"]
        connection.execute(
            sa.text(
                """
                UPDATE lotteries SET name=:name, ticket_price=:ticket_price,
                    schedule=CAST(:schedule AS jsonb), sales_cutoff_minutes=2,
                    is_active=true,
                    next_draw_number=GREATEST(next_draw_number, :draw_number),
                    next_ticket_number=GREATEST(next_ticket_number, :ticket_number)
                WHERE id=:id
                """
            ),
            {
                "id": row["id"],
                "name": name,
                "ticket_price": daily["ticket_price"],
                "schedule": json.dumps({"draw_time": draw_time}),
                "draw_number": daily["next_draw_number"],
                "ticket_number": daily["next_ticket_number"],
            },
        )

    if not live_tickets:
        for table, kind in ACCOUNT_TABLES:
            _move_balance(
                connection,
                table=table,
                kind=kind,
                source_id=daily["id"],
                target_id=named["pll"],
            )
        daily_base = connection.execute(
            sa.text("SELECT base_amount FROM jackpot_accounts WHERE lottery_id=:id"),
            {"id": named["pll"]},
        ).scalar_one()
        # The transferred current jackpot belongs to PLL; preserve its reset base.
        original_base = connection.execute(
            sa.text("SELECT base_amount FROM jackpot_accounts WHERE lottery_id=:id"),
            {"id": daily["id"]},
        ).scalar_one()
        connection.execute(
            sa.text(
                "UPDATE jackpot_accounts SET base_amount=:base WHERE lottery_id=:id"
            ),
            {"base": original_base or daily_base, "id": named["pll"]},
        )
    _set_jackpot(connection, named["pss"], "pss", OWNER_JACKPOT)
    _set_jackpot(connection, named["khan"], "khan", OWNER_JACKPOT)
    connection.execute(
        sa.text(
            "UPDATE lotteries SET name='Архив общей Daily 4/15', is_active=false "
            "WHERE id=:id"
        ),
        {"id": daily["id"]},
    )
    if live_tickets:
        connection.execute(
            sa.text("UPDATE lotteries SET is_active=false WHERE id=:id"),
            {"id": named["pll"]},
        )


def downgrade() -> None:
    raise RuntimeError(
        "Independent Daily funds cannot be recombined without an owner decision."
    )
