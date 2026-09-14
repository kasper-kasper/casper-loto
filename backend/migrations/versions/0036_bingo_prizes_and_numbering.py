"""Separate Bingo pool positions from purchased ticket numbers.

Revision ID: 0036_bingo_prizes_and_numbering
Revises: 0035_shadow_to_code
Create Date: 2026-09-14
"""

import secrets
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_bingo_prizes_and_numbering"
down_revision: str | Sequence[str] | None = "0035_shadow_to_code"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Purchase transactions lock this same row before assigning official numbers.
    # Holding it for the migration keeps the counter reset race-free.
    op.execute(sa.text("SELECT id FROM lotteries WHERE code = 'bingo' FOR UPDATE"))
    op.drop_constraint("uq_bingo_pool_serial", "bingo_pool_tickets", type_="unique")
    op.drop_constraint(
        "uq_bingo_pool_tickets_public_number",
        "bingo_pool_tickets",
        type_="unique",
    )
    op.alter_column(
        "bingo_pool_tickets", "public_number", new_column_name="pool_position"
    )
    op.create_unique_constraint(
        "uq_bingo_pool_position",
        "bingo_pool_tickets",
        ["draw_id", "pool_position"],
    )
    op.create_check_constraint(
        "ck_bingo_pool_tickets_bingo_pool_position_positive",
        "bingo_pool_tickets",
        "pool_position >= 1",
    )
    op.execute(
        sa.text(
            """
            UPDATE lotteries AS lottery
            SET next_ticket_number = COALESCE((
                SELECT MAX(ticket.public_number) + 1
                FROM tickets AS ticket
                WHERE ticket.lottery_id = lottery.id
            ), 1)
            WHERE lottery.code = 'bingo'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE draws AS draw
            SET configuration_snapshot = COALESCE(
                draw.configuration_snapshot, '{}'::jsonb
            )
                || jsonb_build_object(
                    'bingo_tour_moves', jsonb_build_array(18, 34),
                    'bingo_jackpot_move', 28
                )
            FROM lotteries AS lottery
            WHERE lottery.id = draw.lottery_id
              AND lottery.code = 'bingo'
              AND draw.status = 'SCHEDULED'
            """
        )
    )
    _seed_kasper_sets()


def _seed_kasper_sets() -> None:
    connection = op.get_bind()
    draw_ids = connection.execute(
        sa.text(
            """
            SELECT draw.id
            FROM draws AS draw
            JOIN lotteries AS lottery ON lottery.id = draw.lottery_id
            WHERE lottery.code = 'bingo' AND draw.status = 'SCHEDULED'
            """
        )
    ).scalars()
    random = secrets.SystemRandom()
    fixed = (2, 9, 16, 28)
    update = sa.text(
        "UPDATE bingo_pool_tickets SET numbers=:numbers WHERE id=:id"
    ).bindparams(sa.bindparam("numbers", type_=sa.ARRAY(sa.Integer())))
    for draw_id in draw_ids:
        rows = list(
            connection.execute(
                sa.text(
                    """
                    SELECT id, numbers, ticket_id
                    FROM bingo_pool_tickets
                    WHERE draw_id=:draw_id
                    ORDER BY pool_position DESC
                    """
                ),
                {"draw_id": draw_id},
            ).mappings()
        )
        seen = {tuple(sorted(row["numbers"])) for row in rows}
        available = [
            row
            for row in rows
            if row["ticket_id"] is None and set(fixed).issubset(row["numbers"])
        ]
        candidates = [
            row
            for row in rows
            if row["ticket_id"] is None and not set(fixed).issubset(row["numbers"])
        ]
        for row in candidates[: max(0, 100 - len(available))]:
            while True:
                remainder = random.sample(
                    [number for number in range(1, 61) if number not in fixed], 8
                )
                shuffled = random.sample((*fixed, *remainder), 12)
                numbers = tuple(
                    number
                    for index in range(0, 12, 4)
                    for number in sorted(shuffled[index : index + 4])
                )
                identity = tuple(sorted(numbers))
                if identity not in seen:
                    seen.add(identity)
                    break
            connection.execute(update, {"id": row["id"], "numbers": list(numbers)})


def downgrade() -> None:
    op.drop_constraint(
        "ck_bingo_pool_tickets_bingo_pool_position_positive",
        "bingo_pool_tickets",
        type_="check",
    )
    op.drop_constraint("uq_bingo_pool_position", "bingo_pool_tickets", type_="unique")
    op.alter_column(
        "bingo_pool_tickets", "pool_position", new_column_name="public_number"
    )
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id, ROW_NUMBER() OVER (ORDER BY draw_id, public_number) AS value
                FROM bingo_pool_tickets
            )
            UPDATE bingo_pool_tickets AS ticket
            SET public_number = ranked.value
            FROM ranked
            WHERE ranked.id = ticket.id
            """
        )
    )
    op.create_unique_constraint(
        "uq_bingo_pool_serial",
        "bingo_pool_tickets",
        ["draw_id", "public_number"],
    )
    op.create_unique_constraint(
        "uq_bingo_pool_tickets_public_number",
        "bingo_pool_tickets",
        ["public_number"],
    )
