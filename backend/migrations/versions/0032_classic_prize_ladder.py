"""Configure the classic 6/36 ticket price and prize ladder base.

Revision ID: 0032_classic_prizes
Revises: 0031_khan_classic
Create Date: 2026-09-04
"""

import json
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0032_classic_prizes"
down_revision: str | Sequence[str] | None = "0031_khan_classic"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TICKET_PRICE = 48_000
BASE_JACKPOT = 30_000_000


def upgrade() -> None:
    connection = op.get_bind()
    lottery = (
        connection.execute(
            sa.text(
                """
                SELECT l.id, l.ticket_price, j.id AS jackpot_id,
                       j.base_amount, j.balance
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

    connection.execute(
        sa.text(
            """
            UPDATE lotteries
            SET ticket_price = :ticket_price, updated_at = now()
            WHERE id = :lottery_id
            """
        ),
        {"ticket_price": TICKET_PRICE, "lottery_id": lottery["id"]},
    )
    connection.execute(
        sa.text(
            """
            UPDATE jackpot_accounts
            SET base_amount = :base_jackpot,
                version = version + 1,
                updated_at = now()
            WHERE id = :jackpot_id
            """
        ),
        {"base_jackpot": BASE_JACKPOT, "jackpot_id": lottery["jackpot_id"]},
    )
    connection.execute(
        sa.text(
            """
            UPDATE draws
            SET configuration_snapshot = configuration_snapshot ||
                    jsonb_build_object(
                        'ticket_price', CAST(:ticket_price AS bigint),
                        'base_jackpot', CAST(:base_jackpot AS bigint)
                    ),
                updated_at = now()
            WHERE lottery_id = :lottery_id AND status = 'SCHEDULED'
            """
        ),
        {
            "ticket_price": TICKET_PRICE,
            "base_jackpot": BASE_JACKPOT,
            "lottery_id": lottery["id"],
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
                    :id, :admin_user_id, 'UPDATE', 'lottery_configuration',
                    :lottery_id, CAST(:old_values AS jsonb),
                    CAST(:new_values AS jsonb), :reason, now()
                )
                """
            ),
            {
                "id": uuid4(),
                "admin_user_id": admin_user_id,
                "lottery_id": lottery["id"],
                "old_values": json.dumps(
                    {
                        "ticket_price": lottery["ticket_price"],
                        "base_jackpot": lottery["base_amount"],
                        "current_jackpot": lottery["balance"],
                    }
                ),
                "new_values": json.dumps(
                    {
                        "ticket_price": TICKET_PRICE,
                        "base_jackpot": BASE_JACKPOT,
                        "current_jackpot": lottery["balance"],
                        "payouts": {
                            "2": TICKET_PRICE // 4,
                            "3": TICKET_PRICE,
                            "4": TICKET_PRICE * 10,
                            "5": TICKET_PRICE * 100,
                            "6": "jackpot",
                        },
                    }
                ),
                "reason": "Новая цена и призовая лестница лотереи 6 из 36",
            },
        )


def downgrade() -> None:
    raise RuntimeError(
        "Classic 6/36 price and payout configuration is intentionally irreversible."
    )
