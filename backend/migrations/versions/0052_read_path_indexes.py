"""Indexes for player ticket groups and upcoming lottery draws."""

from alembic import op
from sqlalchemy import text

revision = "0052_read_path_indexes"
down_revision = "0051_distribution_results"
branch_labels = None
depends_on = None


def ensure_index(name: str, table: str, columns: list[str]) -> None:
    existing = (
        op.get_bind()
        .execute(
            text("""
        SELECT i.indisvalid, i.indisunique, t.relname AS table_name,
            ARRAY(SELECT a.attname FROM unnest(i.indkey) WITH ORDINALITY k(num,ord)
                  JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.num
                  ORDER BY k.ord) AS columns,
            i.indpred IS NULL AND i.indexprs IS NULL AS plain
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_index i ON i.indexrelid=c.oid JOIN pg_class t ON t.oid=i.indrelid
        WHERE c.relname=:name AND n.nspname=current_schema()
    """),
            {"name": name},
        )
        .mappings()
        .one_or_none()
    )
    if existing is not None:
        if (
            existing["table_name"] != table
            or list(existing["columns"]) != columns
            or existing["indisunique"]
            or not existing["plain"]
        ):
            raise RuntimeError(f"Unexpected index definition: {name}")
        if existing["indisvalid"]:
            return
        op.drop_index(name, table_name=table, postgresql_concurrently=True)
    op.create_index(name, table, columns, postgresql_concurrently=True)


def upgrade() -> None:
    # Production purchases continue during construction; never lock the full
    # ticket table for the duration of an ordinary CREATE INDEX.
    with op.get_context().autocommit_block():
        ensure_index(
            "ix_ticket_user_draw_status",
            "tickets",
            ["user_id", "draw_id", "status"],
        )
        ensure_index(
            "ix_draw_lottery_status_scheduled",
            "draws",
            ["lottery_id", "status", "scheduled_at"],
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_draw_lottery_status_scheduled",
            table_name="draws",
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_ticket_user_draw_status",
            table_name="tickets",
            postgresql_concurrently=True,
        )
