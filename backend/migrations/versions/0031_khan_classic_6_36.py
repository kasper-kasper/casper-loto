"""Convert KHAN future draws to the classic 6/36 format.

Revision ID: 0031_khan_classic
Revises: 0030_fast_cutoff_fix
Create Date: 2026-09-04
"""

import json
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "0031_khan_classic"
down_revision: str | Sequence[str] | None = "0030_fast_cutoff_fix"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TARGET_JACKPOT = 33_456_000


def _ledger_adjustment(
    connection: Connection,
    *,
    account_kind: str,
    account_id: object,
    transaction_type: str,
    amount: int,
    before: int,
    after: int,
    lottery_id: object,
    idempotency_key: str,
    details: dict[str, object],
    user_id: object | None = None,
) -> None:
    connection.execute(
        sa.text(
            """
            INSERT INTO ledger_transactions (
                id, operation_id, idempotency_key, account_kind, account_id,
                type, amount, balance_before, balance_after, user_id,
                lottery_id, created_at, metadata
            ) VALUES (
                :id, :operation_id, :idempotency_key, :account_kind, :account_id,
                :type, :amount, :before, :after, :user_id,
                :lottery_id, now(), CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "id": uuid4(),
            "operation_id": uuid4(),
            "idempotency_key": idempotency_key,
            "account_kind": account_kind,
            "account_id": account_id,
            "type": transaction_type,
            "amount": amount,
            "before": before,
            "after": after,
            "user_id": user_id,
            "lottery_id": lottery_id,
            "metadata": json.dumps(details),
        },
    )


def upgrade() -> None:
    connection = op.get_bind()
    lottery = (
        connection.execute(
            sa.text(
                """
                SELECT l.id, l.name, l.ruleset_code, l.numbers_to_pick,
                       l.max_number, l.ticket_price, j.id AS jackpot_id,
                       j.balance AS jackpot_balance, j.base_amount
                FROM lotteries AS l
                JOIN jackpot_accounts AS j ON j.lottery_id = l.id
                WHERE l.code = 'khan'
                FOR UPDATE OF l, j
                """
            )
        )
        .mappings()
        .one_or_none()
    )
    if lottery is None:
        return
    lottery_id = lottery["id"]
    refunds = (
        connection.execute(
            sa.text(
                """
                SELECT t.user_id, SUM(t.purchase_price)::bigint AS amount,
                       COUNT(*)::integer AS ticket_count,
                       array_agg(t.id ORDER BY t.public_number) AS ticket_ids
                FROM tickets AS t
                JOIN draws AS d ON d.id = t.draw_id
                WHERE t.lottery_id = :lottery_id
                  AND t.status = 'PURCHASED'
                  AND d.status = 'SCHEDULED'
                GROUP BY t.user_id
                ORDER BY t.user_id
                """
            ),
            {"lottery_id": lottery_id},
        )
        .mappings()
        .all()
    )
    total_refund = sum(int(row["amount"]) for row in refunds)
    jackpot_before = int(lottery["jackpot_balance"])
    if total_refund > jackpot_before:
        raise RuntimeError("Classic 6/36 jackpot cannot cover ticket refunds.")

    connection.execute(
        sa.text(
            """
            WITH refunded AS (
                SELECT t.draw_id, COUNT(*)::integer AS ticket_count,
                       SUM(t.purchase_price)::bigint AS total_sales
                FROM tickets AS t
                JOIN draws AS d ON d.id = t.draw_id
                WHERE t.lottery_id = :lottery_id
                  AND t.status = 'PURCHASED'
                  AND d.status = 'SCHEDULED'
                GROUP BY t.draw_id
            )
            UPDATE draws AS d
            SET ticket_count = d.ticket_count - refunded.ticket_count,
                total_sales = d.total_sales - refunded.total_sales
            FROM refunded
            WHERE d.id = refunded.draw_id
            """
        ),
        {"lottery_id": lottery_id},
    )

    for row in refunds:
        before = int(
            connection.execute(
                sa.text(
                    "SELECT amount FROM balances WHERE user_id = :user_id FOR UPDATE"
                ),
                {"user_id": row["user_id"]},
            ).scalar_one()
        )
        amount = int(row["amount"])
        after = before + amount
        connection.execute(
            sa.text(
                """
                UPDATE balances
                SET amount = :after, version = version + 1, updated_at = now()
                WHERE user_id = :user_id
                """
            ),
            {"after": after, "user_id": row["user_id"]},
        )
        _ledger_adjustment(
            connection,
            account_kind="USER_BALANCE",
            account_id=row["user_id"],
            transaction_type="TICKET_REFUND",
            amount=amount,
            before=before,
            after=after,
            user_id=row["user_id"],
            lottery_id=lottery_id,
            idempotency_key=f"migration:0031:khan-refund:user:{row['user_id']}",
            details={
                "reason": "6 из 36 format transition",
                "ticket_count": int(row["ticket_count"]),
                "ticket_ids": [str(value) for value in row["ticket_ids"]],
            },
        )

    after_refund = jackpot_before - total_refund
    if total_refund:
        _ledger_adjustment(
            connection,
            account_kind="JACKPOT",
            account_id=lottery["jackpot_id"],
            transaction_type="TICKET_REFUND",
            amount=-total_refund,
            before=jackpot_before,
            after=after_refund,
            lottery_id=lottery_id,
            idempotency_key="migration:0031:khan-refund:jackpot",
            details={
                "reason": "6 из 36 format transition",
                "refunded_ticket_total": total_refund,
            },
        )
    _ledger_adjustment(
        connection,
        account_kind="JACKPOT",
        account_id=lottery["jackpot_id"],
        transaction_type="SYSTEM_ADJUSTMENT",
        amount=TARGET_JACKPOT - after_refund,
        before=after_refund,
        after=TARGET_JACKPOT,
        lottery_id=lottery_id,
        idempotency_key="migration:0031:khan-jackpot-target",
        details={
            "reason": "Owner-approved 6 из 36 opening jackpot",
            "source": "format_transition",
        },
    )
    connection.execute(
        sa.text(
            """
            UPDATE jackpot_accounts
            SET balance = :target, version = version + 1, updated_at = now()
            WHERE id = :jackpot_id
            """
        ),
        {"target": TARGET_JACKPOT, "jackpot_id": lottery["jackpot_id"]},
    )
    connection.execute(
        sa.text(
            """
            UPDATE tickets AS t
            SET status = 'REFUNDED', settled_at = now()
            FROM draws AS d
            WHERE t.draw_id = d.id
              AND t.lottery_id = :lottery_id
              AND t.status = 'PURCHASED'
              AND d.status = 'SCHEDULED'
            """
        ),
        {"lottery_id": lottery_id},
    )
    admin_user_id = connection.execute(
        sa.text(
            """
            SELECT id FROM users
            WHERE is_admin = true
            ORDER BY (telegram_id = 1201541335) DESC, created_at
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if admin_user_id is not None:
        connection.execute(
            sa.text(
                """
                INSERT INTO admin_audit_log (
                    id, admin_user_id, action, entity_type, entity_id,
                    old_values, new_values, reason, created_at
                ) VALUES (
                    :id, :admin_user_id, 'UPDATE', 'lottery', :lottery_id,
                    CAST(:old_values AS jsonb), CAST(:new_values AS jsonb),
                    :reason, now()
                )
                """
            ),
            {
                "id": uuid4(),
                "admin_user_id": admin_user_id,
                "lottery_id": lottery_id,
                "old_values": json.dumps(
                    {
                        "name": lottery["name"],
                        "ruleset_code": lottery["ruleset_code"],
                        "numbers_to_pick": int(lottery["numbers_to_pick"]),
                        "max_number": int(lottery["max_number"]),
                        "jackpot": jackpot_before,
                    }
                ),
                "new_values": json.dumps(
                    {
                        "name": "6 из 36",
                        "ruleset_code": "classic_6_36",
                        "numbers_to_pick": 6,
                        "max_number": 36,
                        "jackpot": TARGET_JACKPOT,
                        "refunded_tickets": sum(
                            int(row["ticket_count"]) for row in refunds
                        ),
                        "refunded_cas": total_refund,
                    }
                ),
                "reason": "Переход будущих тиражей ХАН-Лото на формат 6 из 36",
            },
        )
    connection.execute(
        sa.text("DELETE FROM favorite_combinations WHERE lottery_id = :lottery_id"),
        {"lottery_id": lottery_id},
    )
    connection.execute(
        sa.text(
            """
            UPDATE lotteries
            SET name = '6 из 36', ruleset_code = 'classic_6_36',
                numbers_to_pick = 6, max_number = 36, updated_at = now()
            WHERE id = :lottery_id
            """
        ),
        {"lottery_id": lottery_id},
    )
    connection.execute(
        sa.text(
            """
            UPDATE draws
            SET configuration_snapshot = jsonb_build_object(
                    'ruleset_code', 'classic_6_36',
                    'ticket_price', CAST(:ticket_price AS bigint),
                    'numbers_to_pick', 6,
                    'max_number', 36,
                    'base_jackpot', CAST(:base_jackpot AS bigint)
                ),
                updated_at = now()
            WHERE lottery_id = :lottery_id AND status = 'SCHEDULED'
            """
        ),
        {
            "ticket_price": lottery["ticket_price"],
            "base_jackpot": lottery["base_amount"],
            "lottery_id": lottery_id,
        },
    )


def downgrade() -> None:
    raise RuntimeError("6 из 36 migration contains ledger refunds and is irreversible.")
