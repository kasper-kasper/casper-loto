"""Allow versioned Dual terms while keeping fixed account protection."""

from alembic import op

revision = "0058_dual_economy_versions"
down_revision = "0057_economy_pause"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_lotteries_dual_configuration"), "lotteries", type_="check"
    )
    op.create_check_constraint(
        "dual_configuration",
        "lotteries",
        "(code <> 'dual' AND ruleset_code NOT IN "
        "('casper_dual_2_12_2_12','casper_dual_2_12_2_12_economy_v2')) OR "
        "(code = 'dual' AND numbers_to_pick = 4 AND max_number = 24 AND "
        "ticket_price IS NOT NULL AND "
        "((ruleset_code = 'casper_dual_2_12_2_12' AND ticket_price = 20000) OR "
        "(ruleset_code = 'casper_dual_2_12_2_12_economy_v2' "
        "AND ticket_price = 40000)))",
    )
    op.execute("DROP TRIGGER trg_dual_jackpot ON jackpot_accounts")
    # Both rows change in one audited transaction. Validate the final state,
    # independent of the ORM's order of UPDATEs, on changes to either row.
    op.execute("""
        CREATE OR REPLACE FUNCTION protect_dual_jackpot() RETURNS trigger AS $$
        DECLARE target uuid; expected bigint;
        BEGIN
            IF TG_TABLE_NAME = 'lotteries' THEN target := NEW.id;
            ELSE target := NEW.lottery_id; END IF;
            SELECT CASE ruleset_code
                WHEN 'casper_dual_2_12_2_12' THEN 5000000
                WHEN 'casper_dual_2_12_2_12_economy_v2' THEN 10000000
                END INTO expected FROM lotteries WHERE id = target AND code = 'dual';
            IF expected IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM jackpot_accounts
                WHERE lottery_id = target
                  AND balance = expected AND base_amount = expected
            ) THEN
                RAISE EXCEPTION 'Dual fixed maximum must match its rules version';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    for table, name in (
        ("jackpot_accounts", "trg_dual_jackpot"),
        ("lotteries", "trg_dual_lottery_terms"),
    ):
        op.execute(f"""
            CREATE CONSTRAINT TRIGGER {name}
            AFTER INSERT OR UPDATE ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION protect_dual_jackpot();
        """)


def downgrade() -> None:
    raise RuntimeError("Approved economy versions require a forward migration.")
