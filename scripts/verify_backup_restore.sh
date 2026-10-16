#!/bin/sh
set -eu

backup_path="${1:-}"
restore_db="k_loto_restore_check_$(cat /proc/sys/kernel/random/uuid | tr -d '-')"
created=false

case "$backup_path" in
  /backups/k-loto-*.dump) ;;
  *) echo "Expected /backups/k-loto-*.dump" >&2; exit 2 ;;
esac
test -f "$backup_path"

cleanup() {
  if [ "$created" = true ]; then
    dropdb -U "$POSTGRES_USER" --if-exists "$restore_db" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
createdb -U "$POSTGRES_USER" "$restore_db"
created=true
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
SELECT 'schema_version:' || version_num FROM alembic_version;
DO $$
DECLARE
  item record;
  mismatches bigint;
BEGIN
  FOR item IN SELECT * FROM (VALUES
    ('USER_BALANCE', 'balances', 'user_id', 'amount'),
    ('JACKPOT', 'jackpot_accounts', 'id', 'balance'),
    ('DISTRIBUTION_FUND', 'distribution_funds', 'id', 'balance'),
    ('LOTTERY_RESERVE', 'lottery_reserves', 'id', 'balance'),
    ('KASPER_FUND', 'kasper_fund_accounts', 'id', 'balance')
  ) AS accounts(kind, table_name, identifier, amount_column)
  LOOP
    EXECUTE format(
      'SELECT count(*) FROM %I a LEFT JOIN '
      '(SELECT account_id,sum(amount) amount FROM ledger_transactions '
      'WHERE account_kind=%L GROUP BY account_id) l ON l.account_id=a.%I '
      'WHERE a.%I<>coalesce(l.amount,0)',
      item.table_name, item.kind, item.identifier, item.amount_column
    ) INTO mismatches;
    IF mismatches <> 0 THEN
      RAISE EXCEPTION 'Restored ledger mismatch: %', item.kind;
    END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_index WHERE NOT indisvalid OR NOT indisready) THEN
    RAISE EXCEPTION 'Invalid restored indexes';
  END IF;
END $$;
SQL
echo "ledger_and_indexes:ok"
echo "restore:ok"
