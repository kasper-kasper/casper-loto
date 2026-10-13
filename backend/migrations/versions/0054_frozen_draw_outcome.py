"""Protect the outcome committed before settlement, including pending draws."""

from alembic import op

revision = "0054_frozen_draw_outcome"
down_revision = "0053_purchase_cancellations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION protect_committed_draw_outcome() RETURNS trigger AS $$
        BEGIN
            IF OLD.winning_numbers IS NOT NULL AND (
                NEW.winning_numbers IS DISTINCT FROM OLD.winning_numbers OR
                NEW.jackpot_opening IS DISTINCT FROM OLD.jackpot_opening OR
                NEW.configuration_snapshot IS DISTINCT FROM
                    OLD.configuration_snapshot OR
                NEW.is_distribution IS DISTINCT FROM OLD.is_distribution
            ) THEN
                RAISE EXCEPTION 'Committed draw outcome is immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_committed_draw_outcome
        BEFORE UPDATE ON draws
        FOR EACH ROW EXECUTE FUNCTION protect_committed_draw_outcome();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_committed_draw_outcome ON draws")
    op.execute("DROP FUNCTION protect_committed_draw_outcome()")
