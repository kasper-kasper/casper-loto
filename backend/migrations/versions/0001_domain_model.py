"""Create the K-Loto domain model.

Revision ID: 0001_domain_model
Revises:
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_domain_model"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(
        *values, name=name, native_enum=False, create_constraint=True, length=32
    )


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
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
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False),
        *timestamps(),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )
    op.create_table(
        "lotteries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("kind", enum("lottery_kind", "WEEKLY", "DAILY"), nullable=False),
        sa.Column("numbers_to_pick", sa.Integer(), nullable=False),
        sa.Column("max_number", sa.Integer(), nullable=False),
        sa.Column("ticket_price", sa.BigInteger(), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("schedule", postgresql.JSONB(), nullable=False),
        sa.Column("sales_cutoff_minutes", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "next_draw_number", sa.BigInteger(), server_default="1", nullable=False
        ),
        sa.Column(
            "next_ticket_number", sa.BigInteger(), server_default="1", nullable=False
        ),
        *timestamps(),
        sa.UniqueConstraint("code", name="uq_lotteries_code"),
        sa.CheckConstraint(
            "numbers_to_pick > 0", name="ck_lotteries_numbers_to_pick_positive"
        ),
        sa.CheckConstraint(
            "max_number >= numbers_to_pick", name="ck_lotteries_max_number_valid"
        ),
        sa.CheckConstraint(
            "ticket_price IS NULL OR ticket_price > 0",
            name="ck_lotteries_ticket_price_positive",
        ),
        sa.CheckConstraint(
            "next_draw_number >= 1", name="ck_lotteries_next_draw_number_positive"
        ),
        sa.CheckConstraint(
            "next_ticket_number >= 1", name="ck_lotteries_next_ticket_number_positive"
        ),
    )
    op.create_table(
        "draws",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lottery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_number", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            enum(
                "draw_status",
                "SCHEDULED",
                "CLOSED",
                "DRAWING",
                "SETTLING",
                "COMPLETED",
                "FAILED",
            ),
            server_default="SCHEDULED",
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sales_close_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("winning_numbers", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_sales", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("total_payout", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("jackpot_opening", sa.BigInteger(), nullable=True),
        sa.Column("jackpot_closing", sa.BigInteger(), nullable=True),
        sa.Column("distribution_opening", sa.BigInteger(), nullable=True),
        sa.Column("distribution_closing", sa.BigInteger(), nullable=True),
        sa.Column("reserve_used", sa.BigInteger(), server_default="0", nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["lottery_id"], ["lotteries.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "lottery_id", "public_number", name="uq_draw_lottery_number"
        ),
        sa.UniqueConstraint("correlation_id", name="uq_draws_correlation_id"),
        sa.CheckConstraint(
            "public_number >= 1", name="ck_draws_public_number_positive"
        ),
        sa.CheckConstraint(
            "sales_close_at <= scheduled_at", name="ck_draws_sales_close_before_draw"
        ),
        sa.CheckConstraint(
            "ticket_count >= 0", name="ck_draws_ticket_count_nonnegative"
        ),
        sa.CheckConstraint("total_sales >= 0", name="ck_draws_total_sales_nonnegative"),
        sa.CheckConstraint(
            "total_payout >= 0", name="ck_draws_total_payout_nonnegative"
        ),
    )
    op.create_index("ix_draw_due", "draws", ["status", "scheduled_at"])
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("public_number", sa.BigInteger(), nullable=False),
        sa.Column("lottery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draw_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numbers", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("purchase_price", sa.BigInteger(), nullable=False),
        sa.Column(
            "purchased_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "status",
            enum("ticket_status", "PURCHASED", "SETTLED"),
            server_default="PURCHASED",
            nullable=False,
        ),
        sa.Column("matches", sa.Integer(), nullable=True),
        sa.Column("prize_amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["lottery_id"], ["lotteries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["draw_id"], ["draws.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "lottery_id", "public_number", name="uq_ticket_lottery_number"
        ),
        sa.CheckConstraint(
            "public_number >= 1", name="ck_tickets_public_number_positive"
        ),
        sa.CheckConstraint(
            "purchase_price > 0", name="ck_tickets_purchase_price_positive"
        ),
        sa.CheckConstraint(
            "prize_amount >= 0", name="ck_tickets_prize_amount_nonnegative"
        ),
        sa.CheckConstraint(
            "matches IS NULL OR matches >= 0", name="ck_tickets_matches_nonnegative"
        ),
    )
    op.create_index("ix_ticket_user_status", "tickets", ["user_id", "status"])
    op.create_index("ix_ticket_draw", "tickets", ["draw_id"])
    op.create_table(
        "balances",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("amount >= 0", name="ck_balances_amount_nonnegative"),
    )
    for table_name in ("jackpot_accounts", "distribution_funds", "lottery_reserves"):
        columns: list[sa.Column | sa.Constraint] = [
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("lottery_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("balance", sa.BigInteger(), server_default="0", nullable=False),
        ]
        if table_name == "jackpot_accounts":
            columns.append(
                sa.Column(
                    "base_amount", sa.BigInteger(), server_default="0", nullable=False
                )
            )
        columns.extend(
            [
                sa.Column("version", sa.Integer(), server_default="1", nullable=False),
                *timestamps(),
                sa.ForeignKeyConstraint(
                    ["lottery_id"], ["lotteries.id"], ondelete="RESTRICT"
                ),
                sa.UniqueConstraint("lottery_id", name=f"uq_{table_name}_lottery_id"),
                sa.CheckConstraint(
                    "balance >= 0", name=f"ck_{table_name}_balance_nonnegative"
                ),
            ]
        )
        if table_name == "jackpot_accounts":
            columns.append(
                sa.CheckConstraint(
                    "base_amount >= 0",
                    name="ck_jackpot_accounts_base_amount_nonnegative",
                )
            )
        op.create_table(table_name, *columns)
    op.create_table(
        "ledger_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column(
            "account_kind",
            enum(
                "ledger_account_kind",
                "USER_BALANCE",
                "JACKPOT",
                "DISTRIBUTION_FUND",
                "LOTTERY_RESERVE",
            ),
            nullable=False,
        ),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type",
            enum(
                "transaction_type",
                "ADMIN_BALANCE_ADJUSTMENT",
                "TICKET_PURCHASE",
                "PRIZE_PAYOUT",
                "JACKPOT_PAYOUT",
                "RESERVE_ADJUSTMENT",
                "SYSTEM_ADJUSTMENT",
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("balance_before", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lottery_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("draw_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lottery_id"], ["lotteries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["draw_id"], ["draws.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_ledger_transactions_idempotency_key"
        ),
        sa.CheckConstraint("amount <> 0", name="ck_ledger_transactions_amount_nonzero"),
        sa.CheckConstraint(
            "balance_after = balance_before + amount",
            name="ck_ledger_transactions_balance_equation",
        ),
        sa.CheckConstraint(
            "balance_before >= 0",
            name="ck_ledger_transactions_balance_before_nonnegative",
        ),
        sa.CheckConstraint(
            "balance_after >= 0",
            name="ck_ledger_transactions_balance_after_nonnegative",
        ),
    )
    op.create_index(
        "ix_ledger_transactions_operation_id", "ledger_transactions", ["operation_id"]
    )
    op.create_index("ix_ledger_created_at", "ledger_transactions", ["created_at"])
    op.create_index(
        "ix_ledger_user_created", "ledger_transactions", ["user_id", "created_at"]
    )
    op.create_table(
        "admin_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "action", enum("audit_action", "CREATE", "UPDATE", "ADJUST"), nullable=False
        ),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("old_values", postgresql.JSONB(), nullable=True),
        sa.Column("new_values", postgresql.JSONB(), nullable=True),
        sa.Column("reason", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_admin_audit_created", "admin_audit_log", ["created_at"])

    op.execute(
        """
        CREATE FUNCTION prevent_completed_draw_mutation() RETURNS trigger AS $$
        BEGIN
            IF OLD.status = 'COMPLETED' THEN
                RAISE EXCEPTION 'completed draws are immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_completed_draw_immutable
        BEFORE UPDATE OR DELETE ON draws
        FOR EACH ROW EXECUTE FUNCTION prevent_completed_draw_mutation();
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_ticket_history() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'purchased tickets cannot be deleted';
            END IF;
            IF OLD.settled_at IS NOT NULL THEN
                RAISE EXCEPTION 'settled tickets are immutable';
            END IF;
            IF OLD.public_number IS DISTINCT FROM NEW.public_number
               OR OLD.lottery_id IS DISTINCT FROM NEW.lottery_id
               OR OLD.draw_id IS DISTINCT FROM NEW.draw_id
               OR OLD.user_id IS DISTINCT FROM NEW.user_id
               OR OLD.numbers IS DISTINCT FROM NEW.numbers
               OR OLD.purchase_price IS DISTINCT FROM NEW.purchase_price
               OR OLD.purchased_at IS DISTINCT FROM NEW.purchased_at THEN
                RAISE EXCEPTION 'purchased ticket game data is immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_ticket_history_immutable
        BEFORE UPDATE OR DELETE ON tickets
        FOR EACH ROW EXECUTE FUNCTION protect_ticket_history();
        """
    )
    op.execute(
        """
        CREATE FUNCTION prevent_ledger_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'ledger transactions are immutable';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_ledger_immutable
        BEFORE UPDATE OR DELETE ON ledger_transactions
        FOR EACH ROW EXECUTE FUNCTION prevent_ledger_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_ledger_immutable ON ledger_transactions")
    op.execute("DROP FUNCTION IF EXISTS prevent_ledger_mutation")
    op.execute("DROP TRIGGER IF EXISTS trg_ticket_history_immutable ON tickets")
    op.execute("DROP FUNCTION IF EXISTS protect_ticket_history")
    op.execute("DROP TRIGGER IF EXISTS trg_completed_draw_immutable ON draws")
    op.execute("DROP FUNCTION IF EXISTS prevent_completed_draw_mutation")
    for table in (
        "admin_audit_log",
        "ledger_transactions",
        "lottery_reserves",
        "distribution_funds",
        "jackpot_accounts",
        "balances",
        "tickets",
        "draws",
        "lotteries",
        "users",
    ):
        op.drop_table(table)
