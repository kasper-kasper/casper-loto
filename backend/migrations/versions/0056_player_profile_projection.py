"""Transactionally maintain rebuildable player display statistics."""

# ruff: noqa: E501 -- SQL expressions stay legible.

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0056_player_profile_projection"
down_revision = "0055_history_delivery_guards"
branch_labels = None
depends_on = None


def execute(script: str) -> None:
    """Asyncpg prepares one SQL command at a time, including function bodies."""
    chunks = script.split("$$ LANGUAGE plpgsql;")
    for chunk in chunks[:-1]:
        op.execute(chunk + "$$ LANGUAGE plpgsql;")
    if chunks[-1].strip():
        op.execute(chunks[-1])


def upgrade() -> None:
    columns = (
        "ticket_count",
        "active_ticket_count",
        "winning_ticket_count",
        "total_spent",
        "total_won",
        "best_win",
        "unread_notification_count",
    )
    op.create_table(
        "player_profile_stats",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        *(
            sa.Column(name, sa.BigInteger(), nullable=False, server_default="0")
            for name in columns
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            " AND ".join(f"{name} >= 0" for name in columns), name="nonnegative"
        ),
    )
    op.create_table(
        "player_lottery_stats",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lottery_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lottery_id"], ["lotteries.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("ticket_count >= 0", name="nonnegative"),
    )
    op.create_index(
        "ix_ticket_profile_recent",
        "tickets",
        ["user_id", "lottery_id", sa.text("purchased_at DESC"), sa.text("id DESC")],
        postgresql_where=sa.text("status <> 'REFUNDED'"),
    )
    # These functions maintain derived display data only. They neither authorize
    # business operations nor change tickets, draws, accounts or ledger entries.
    execute("""
        CREATE FUNCTION initialize_player_profile() RETURNS trigger AS $$
        BEGIN
            INSERT INTO player_profile_stats(user_id)
            SELECT id FROM profile_new_users ORDER BY id ON CONFLICT DO NOTHING;
            RETURN NULL;
        END; $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_initialize_player_profile AFTER INSERT ON users
        REFERENCING NEW TABLE AS profile_new_users
        FOR EACH STATEMENT EXECUTE FUNCTION initialize_player_profile();
    """)
    execute("""
        CREATE FUNCTION project_regular_ticket_insert() RETURNS trigger AS $$
        DECLARE d record;
        BEGIN
            FOR d IN SELECT user_id, count(*) AS tickets,
                count(*) FILTER (WHERE status='PURCHASED') AS active,
                count(*) FILTER (WHERE prize_amount>0) AS winning,
                coalesce(sum(purchase_price) FILTER (WHERE status<>'REFUNDED'),0) AS spent,
                sum(prize_amount) AS won, max(prize_amount) AS best
                FROM profile_new_tickets GROUP BY user_id ORDER BY user_id
            LOOP
                UPDATE player_profile_stats SET ticket_count=ticket_count+d.tickets,
                    active_ticket_count=active_ticket_count+d.active,
                    winning_ticket_count=winning_ticket_count+d.winning,
                    total_spent=total_spent+d.spent, total_won=total_won+d.won,
                    best_win=greatest(best_win,d.best) WHERE user_id=d.user_id;
            END LOOP;
            INSERT INTO player_lottery_stats(user_id,lottery_id,ticket_count)
            SELECT user_id,lottery_id,count(*) FROM profile_new_tickets
            WHERE status<>'REFUNDED' GROUP BY user_id,lottery_id ORDER BY user_id,lottery_id
            ON CONFLICT (user_id,lottery_id) DO UPDATE SET
                ticket_count=player_lottery_stats.ticket_count+EXCLUDED.ticket_count;
            RETURN NULL;
        END; $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_profile_regular_insert AFTER INSERT ON tickets
        REFERENCING NEW TABLE AS profile_new_tickets
        FOR EACH STATEMENT EXECUTE FUNCTION project_regular_ticket_insert();
    """)
    execute("""
        CREATE FUNCTION project_regular_ticket_update() RETURNS trigger AS $$
        DECLARE d record;
        BEGIN
            FOR d IN SELECT n.user_id,
                sum((n.status='PURCHASED')::int-(o.status='PURCHASED')::int) AS active,
                sum((n.prize_amount>0)::int-(o.prize_amount>0)::int) AS winning,
                sum(CASE WHEN n.status<>'REFUNDED' THEN n.purchase_price ELSE 0 END
                    -CASE WHEN o.status<>'REFUNDED' THEN o.purchase_price ELSE 0 END) AS spent,
                sum(n.prize_amount-o.prize_amount) AS won,
                max(n.prize_amount) AS best,
                bool_or(n.prize_amount<o.prize_amount) AS reduced
                FROM profile_new_tickets n JOIN profile_old_tickets o USING(id)
                WHERE n.status IS DISTINCT FROM o.status OR n.prize_amount IS DISTINCT FROM o.prize_amount
                GROUP BY n.user_id ORDER BY n.user_id
            LOOP
                UPDATE player_profile_stats SET active_ticket_count=active_ticket_count+d.active,
                    winning_ticket_count=winning_ticket_count+d.winning,
                    total_spent=total_spent+d.spent, total_won=total_won+d.won,
                    best_win=greatest(best_win,d.best) WHERE user_id=d.user_id;
                -- Normal settlement only increases prizes. Preserve exactness if an
                -- otherwise permitted pre-settlement change reduces an interim prize.
                IF d.reduced THEN
                    UPDATE player_profile_stats SET best_win=(
                        SELECT coalesce(max(prize_amount),0) FROM (
                            SELECT prize_amount FROM tickets WHERE user_id=d.user_id
                            UNION ALL SELECT prize_amount FROM instant_tickets WHERE user_id=d.user_id
                        ) prizes) WHERE user_id=d.user_id;
                END IF;
            END LOOP;
            FOR d IN SELECT n.user_id,n.lottery_id,
                sum((n.status<>'REFUNDED')::int-(o.status<>'REFUNDED')::int) AS delta
                FROM profile_new_tickets n JOIN profile_old_tickets o USING(id)
                GROUP BY n.user_id,n.lottery_id
                HAVING sum((n.status<>'REFUNDED')::int-(o.status<>'REFUNDED')::int)<>0
                ORDER BY n.user_id,n.lottery_id
            LOOP
                INSERT INTO player_lottery_stats(user_id,lottery_id,ticket_count)
                VALUES(d.user_id,d.lottery_id,0) ON CONFLICT DO NOTHING;
                UPDATE player_lottery_stats SET ticket_count=ticket_count+d.delta
                WHERE user_id=d.user_id AND lottery_id=d.lottery_id;
            END LOOP;
            RETURN NULL;
        END; $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_profile_regular_update AFTER UPDATE ON tickets
        REFERENCING NEW TABLE AS profile_new_tickets OLD TABLE AS profile_old_tickets
        FOR EACH STATEMENT EXECUTE FUNCTION project_regular_ticket_update();
    """)
    execute("""
        CREATE FUNCTION project_instant_ticket_insert() RETURNS trigger AS $$
        DECLARE d record;
        BEGIN
            FOR d IN SELECT user_id, count(*) AS tickets,
                count(*) FILTER (WHERE prize_amount>0) AS winning,
                sum(purchase_price) AS spent, sum(prize_amount) AS won,
                max(prize_amount) AS best FROM profile_new_instant
                GROUP BY user_id ORDER BY user_id
            LOOP
                UPDATE player_profile_stats SET ticket_count=ticket_count+d.tickets,
                    winning_ticket_count=winning_ticket_count+d.winning,
                    total_spent=total_spent+d.spent, total_won=total_won+d.won,
                    best_win=greatest(best_win,d.best) WHERE user_id=d.user_id;
            END LOOP;
            RETURN NULL;
        END; $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_profile_instant_insert AFTER INSERT ON instant_tickets
        REFERENCING NEW TABLE AS profile_new_instant
        FOR EACH STATEMENT EXECUTE FUNCTION project_instant_ticket_insert();
    """)
    for operation, relation, sign in (
        ("INSERT", "profile_new_notifications", "1"),
        ("DELETE", "profile_old_notifications", "-1"),
        ("UPDATE", "profile_new_notifications", "1"),
    ):
        query = f"SELECT user_id, {sign} AS delta FROM {relation} WHERE read_at IS NULL AND type<>'DRAW_RESULT'"
        if operation == "UPDATE":
            query += " UNION ALL SELECT user_id,-1 AS delta FROM profile_old_notifications WHERE read_at IS NULL AND type<>'DRAW_RESULT'"
        name = "project_profile_notifications_" + operation.lower()
        execute(f"""
            CREATE FUNCTION {name}() RETURNS trigger AS $$
            DECLARE d record;
            BEGIN
                FOR d IN SELECT user_id,sum(delta) AS delta FROM ({query}) changes
                    GROUP BY user_id HAVING sum(delta)<>0 ORDER BY user_id
                LOOP
                    UPDATE player_profile_stats SET unread_notification_count=unread_notification_count+d.delta
                    WHERE user_id=d.user_id;
                END LOOP;
                RETURN NULL;
            END; $$ LANGUAGE plpgsql;
        """)
        references = {
            "INSERT": "NEW TABLE AS profile_new_notifications",
            "DELETE": "OLD TABLE AS profile_old_notifications",
            "UPDATE": "NEW TABLE AS profile_new_notifications OLD TABLE AS profile_old_notifications",
        }[operation]
        execute(f"""
            CREATE TRIGGER trg_profile_notifications_{operation.lower()}
            AFTER {operation} ON user_notifications REFERENCING {references}
            FOR EACH STATEMENT EXECUTE FUNCTION {name}();
        """)
    execute("""
        CREATE FUNCTION rebuild_player_profiles() RETURNS void AS $$
        BEGIN
            -- One consistent rebuild. Readers retain the old committed projection;
            -- writers wait, so no concurrent purchase/payout can be lost or doubled.
            IF current_setting('transaction_isolation') <> 'read committed' THEN
                RAISE EXCEPTION 'Profile rebuild requires READ COMMITTED isolation';
            END IF;
            LOCK TABLE users,tickets,instant_tickets,user_notifications IN SHARE ROW EXCLUSIVE MODE;
            INSERT INTO player_profile_stats(user_id,ticket_count,active_ticket_count,
                winning_ticket_count,total_spent,total_won,best_win,unread_notification_count)
            WITH activity AS (
                SELECT user_id,count(*) AS tickets,
                    count(*) FILTER (WHERE status='PURCHASED') AS active,
                    count(*) FILTER (WHERE prize_amount>0) AS winning,
                    coalesce(sum(purchase_price) FILTER (WHERE status<>'REFUNDED'),0) AS spent,
                    sum(prize_amount) AS won,max(prize_amount) AS best
                    FROM tickets GROUP BY user_id
                UNION ALL
                SELECT user_id,count(*),0,count(*) FILTER (WHERE prize_amount>0),
                    sum(purchase_price),sum(prize_amount),max(prize_amount)
                    FROM instant_tickets GROUP BY user_id
            ), totals AS (
                SELECT user_id,sum(tickets) AS tickets,sum(active) AS active,
                    sum(winning) AS winning,sum(spent) AS spent,sum(won) AS won,max(best) AS best
                    FROM activity GROUP BY user_id
            ), unread AS (
                SELECT user_id,count(*) AS unread FROM user_notifications
                WHERE read_at IS NULL AND type<>'DRAW_RESULT' GROUP BY user_id
            )
            SELECT u.id,coalesce(t.tickets,0),coalesce(t.active,0),coalesce(t.winning,0),
                coalesce(t.spent,0),coalesce(t.won,0),coalesce(t.best,0),coalesce(n.unread,0)
                FROM users u LEFT JOIN totals t ON t.user_id=u.id LEFT JOIN unread n ON n.user_id=u.id
                ORDER BY u.id
            ON CONFLICT (user_id) DO UPDATE SET ticket_count=EXCLUDED.ticket_count,
                active_ticket_count=EXCLUDED.active_ticket_count,winning_ticket_count=EXCLUDED.winning_ticket_count,
                total_spent=EXCLUDED.total_spent,total_won=EXCLUDED.total_won,best_win=EXCLUDED.best_win,
                unread_notification_count=EXCLUDED.unread_notification_count;
            DELETE FROM player_lottery_stats;
            INSERT INTO player_lottery_stats(user_id,lottery_id,ticket_count)
                SELECT user_id,lottery_id,count(*) FROM tickets WHERE status<>'REFUNDED'
                GROUP BY user_id,lottery_id ORDER BY user_id,lottery_id;
        END; $$ LANGUAGE plpgsql;
        SELECT rebuild_player_profiles();
    """)


def downgrade() -> None:
    for operation in ("insert", "update", "delete"):
        execute(
            f"DROP TRIGGER trg_profile_notifications_{operation} ON user_notifications"
        )
        execute(f"DROP FUNCTION project_profile_notifications_{operation}()")
    for table, trigger, function in (
        ("tickets", "trg_profile_regular_insert", "project_regular_ticket_insert"),
        ("tickets", "trg_profile_regular_update", "project_regular_ticket_update"),
        (
            "instant_tickets",
            "trg_profile_instant_insert",
            "project_instant_ticket_insert",
        ),
        ("users", "trg_initialize_player_profile", "initialize_player_profile"),
    ):
        execute(f"DROP TRIGGER {trigger} ON {table}")
        execute(f"DROP FUNCTION {function}()")
    execute("DROP FUNCTION rebuild_player_profiles()")
    op.drop_index("ix_ticket_profile_recent", table_name="tickets")
    op.drop_table("player_lottery_stats")
    op.drop_table("player_profile_stats")
