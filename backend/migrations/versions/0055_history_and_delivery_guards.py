"""Close immutable-history gaps and preserve ambiguous delivery outcomes."""

# ruff: noqa: E501 -- Keep SQL guards readable.

from alembic import op

revision = "0055_history_delivery_guards"
down_revision = "0054_frozen_draw_outcome"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_draw_lottery_schedule", "draws", ["lottery_id", "scheduled_at"]
    )
    op.execute("""
        CREATE FUNCTION reject_history_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '% history is immutable', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_instant_ticket_immutable
        BEFORE UPDATE OR DELETE ON instant_tickets
        FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
    """)
    op.execute("""
        CREATE TRIGGER trg_admin_audit_immutable
        BEFORE UPDATE OR DELETE ON admin_audit_log
        FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
    """)
    op.execute("""
        CREATE FUNCTION protect_extended_ticket_history() RETURNS trigger AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id OR
               NEW.source IS DISTINCT FROM OLD.source OR
               NEW.second_draw_id IS DISTINCT FROM OLD.second_draw_id OR
               (OLD.dual_night_matches IS NOT NULL AND
                NEW.dual_night_matches IS DISTINCT FROM OLD.dual_night_matches) OR
               (OLD.dual_dawn_matches IS NOT NULL AND
                NEW.dual_dawn_matches IS DISTINCT FROM OLD.dual_dawn_matches) THEN
                RAISE EXCEPTION 'Purchased ticket identity and round results are immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_extended_ticket_history
        BEFORE UPDATE ON tickets
        FOR EACH ROW EXECUTE FUNCTION protect_extended_ticket_history();
    """)
    op.create_check_constraint(
        "dual_configuration",
        "lotteries",
        "(code <> 'dual' AND ruleset_code <> 'casper_dual_2_12_2_12') OR "
        "(code = 'dual' AND ruleset_code = 'casper_dual_2_12_2_12' AND "
        "ticket_price IS NOT NULL AND ticket_price = 20000 AND numbers_to_pick = 4 AND max_number = 24)",
    )
    op.execute("""
        CREATE FUNCTION protect_dual_jackpot() RETURNS trigger AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM lotteries WHERE id = NEW.lottery_id
                       AND code = 'dual') AND
               (NEW.balance <> 5000000 OR NEW.base_amount <> 5000000) THEN
                RAISE EXCEPTION 'Casper Dual requires a fixed 5000000 CAS jackpot';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_dual_jackpot
        BEFORE INSERT OR UPDATE ON jackpot_accounts
        FOR EACH ROW EXECUTE FUNCTION protect_dual_jackpot();
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM jackpot_accounts j JOIN lotteries l
                       ON l.id = j.lottery_id WHERE l.code = 'dual' AND
                       (j.balance <> 5000000 OR j.base_amount <> 5000000)) THEN
                RAISE EXCEPTION 'Existing Dual jackpot needs a ledgered correction before upgrade';
            END IF;
        END $$;
    """)
    op.drop_constraint(
        op.f("ck_notification_outbox_notification_status"),
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "notification_status",
        "notification_outbox",
        "status IN ('PENDING','PROCESSING','SENT','FAILED','CANCELLED','UNCERTAIN')",
    )

    # Earlier workers did not distinguish transport rejection from a lost ack.
    # Preserve that uncertainty instead of replaying possibly delivered messages.
    op.execute("""
        UPDATE notification_outbox SET status = 'UNCERTAIN', locked_at = NULL,
            last_error = 'legacy_delivery_unverified' WHERE status = 'FAILED';
    """)


def downgrade() -> None:
    raise RuntimeError(
        "History and uncertain delivery protection require a forward migration."
    )
