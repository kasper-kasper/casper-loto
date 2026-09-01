#!/bin/sh
set -eu

backup_path="${1:-}"
restore_db="k_loto_restore_check"

case "$backup_path" in
  /backups/k-loto-*.dump) ;;
  *) echo "Expected /backups/k-loto-*.dump" >&2; exit 2 ;;
esac
test -f "$backup_path"

cleanup() {
  dropdb -U "$POSTGRES_USER" --if-exists "$restore_db" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
cleanup
createdb -U "$POSTGRES_USER" "$restore_db"
pg_restore -U "$POSTGRES_USER" --exit-on-error --no-owner \
  --dbname "$restore_db" "$backup_path"

schema_count="$(psql -U "$POSTGRES_USER" -d "$restore_db" -Atc \
  'SELECT count(*) FROM alembic_version')"
test "$schema_count" = "1"
echo "schema:ok"

psql -U "$POSTGRES_USER" -d "$restore_db" -v ON_ERROR_STOP=1 -At <<'SQL'
SELECT 'users:' || count(*) FROM users;
SELECT 'draws:' || count(*) FROM draws;
SELECT 'tickets:' || count(*) FROM tickets;
SELECT 'ledger:' || count(*) FROM ledger_transactions;
SQL
echo "restore:ok"
