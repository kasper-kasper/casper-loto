"""Convert future SHADOW draws to ordered four-digit CODE.

Revision ID: 0035_shadow_to_code
Revises: 0034_pll_second_slot
Create Date: 2026-09-05
"""

import json
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0035_shadow_to_code"
down_revision: str | Sequence[str] | None = "0034_pll_second_slot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
                WHERE l.code = 'shadow'
                FOR UPDATE OF l, j
                """
            )
        )
        .mappings()
        .one_or_none()
    )
    if lottery is None or lottery["ruleset_code"] == "code_4_digits":
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
        raise RuntimeError("CODE transition jackpot cannot cover ticket refunds.")

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
                total_sales = d.total_sales - refunded.total_sales,
                updated_at = now()
            FROM refunded
            WHERE d.id = refunded.draw_id
            """
        ),
        {"lottery_id": lottery_id},
    )

    for row in refunds:
        balance_before = int(
            connection.execute(
                sa.text(
                    "SELECT amount FROM balances WHERE user_id = :user_id FOR UPDATE"
                ),
                {"user_id": row["user_id"]},
            ).scalar_one()
        )
        amount = int(row["amount"])
        balance_after = balance_before + amount
        connection.execute(
            sa.text(
                """
                UPDATE balances
                SET amount = :after, version = version + 1, updated_at = now()
                WHERE user_id = :user_id
                """
            ),
            {"after": balance_after, "user_id": row["user_id"]},
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO ledger_transactions (
                    id, operation_id, idempotency_key, account_kind, account_id,
                    type, amount, balance_before, balance_after, user_id,
                    lottery_id, created_at, metadata
                ) VALUES (
                    :id, :operation_id, :key, 'USER_BALANCE', :user_id,
                    'TICKET_REFUND', :amount, :before, :after, :user_id,
                    :lottery_id, now(), CAST(:metadata AS jsonb)
                )
                """
            ),
            {
                "id": uuid4(),
                "operation_id": uuid4(),
                "key": f"migration:0035:code-refund:user:{row['user_id']}",
                "user_id": row["user_id"],
                "lottery_id": lottery_id,
                "amount": amount,
                "before": balance_before,
                "after": balance_after,
                "metadata": json.dumps(
                    {
                        "reason": "SHADOW to CODE format transition",
                        "ticket_count": int(row["ticket_count"]),
                        "ticket_ids": [str(value) for value in row["ticket_ids"]],
                    }
                ),
            },
        )

    jackpot_after = jackpot_before - total_refund
    if total_refund:
        connection.execute(
            sa.text(
                """
                UPDATE jackpot_accounts
                SET balance = :after, version = version + 1, updated_at = now()
                WHERE id = :jackpot_id
                """
            ),
            {"after": jackpot_after, "jackpot_id": lottery["jackpot_id"]},
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO ledger_transactions (
                    id, operation_id, idempotency_key, account_kind, account_id,
                    type, amount, balance_before, balance_after, lottery_id,
                    created_at, metadata
                ) VALUES (
                    :id, :operation_id, 'migration:0035:code-refund:jackpot',
                    'JACKPOT', :jackpot_id, 'TICKET_REFUND', :amount,
                    :before, :after, :lottery_id, now(), CAST(:metadata AS jsonb)
                )
                """
            ),
            {
                "id": uuid4(),
                "operation_id": uuid4(),
                "jackpot_id": lottery["jackpot_id"],
                "lottery_id": lottery_id,
                "amount": -total_refund,
                "before": jackpot_before,
                "after": jackpot_after,
                "metadata": json.dumps(
                    {
                        "reason": "SHADOW to CODE format transition",
                        "refunded_ticket_total": total_refund,
                    }
                ),
            },
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
    connection.execute(
        sa.text("DELETE FROM favorite_combinations WHERE lottery_id = :lottery_id"),
        {"lottery_id": lottery_id},
    )
    connection.execute(
        sa.text(
            """
            UPDATE lotteries
            SET name = 'CODE', ruleset_code = 'code_4_digits',
                numbers_to_pick = 4, max_number = 9, updated_at = now()
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
                    'ruleset_code', 'code_4_digits',
                    'ticket_price', CAST(:ticket_price AS bigint),
                    'numbers_to_pick', 4,
                    'max_number', 9,
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
                        "name": "CODE",
                        "ruleset_code": "code_4_digits",
                        "numbers_to_pick": 4,
                        "max_number": 9,
                        "ticket_price": int(lottery["ticket_price"]),
                        "jackpot": jackpot_after,
                        "refunded_tickets": sum(
                            int(row["ticket_count"]) for row in refunds
                        ),
                        "refunded_cas": total_refund,
                    }
                ),
                "reason": "Обновление SHADOW до четырёхзначной лотереи CODE",
            },
        )


def downgrade() -> None:
    raise RuntimeError("CODE migration contains ledger refunds and is irreversible.")
