#!/bin/sh
set -eu

# Separate lock: maintenance takes this as well as the publication lock.
exec 9>/run/lock/k-loto-backup.lock
flock -x 9

cd /opt/k-loto
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db \
  sh -c 'set -eu; target="/backups/k-loto-'"$stamp"'.dump"; \
    trap '\''rm -f "$target.partial"'\'' EXIT; \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$target.partial"; \
    pg_restore --list "$target.partial" >/dev/null; \
    chmod 600 "$target.partial"; mv "$target.partial" "$target"'
# The backup lock remains held; retention logic is centralized in maintenance.
python3 -c 'from scripts.server_maintenance import prune_database_backups; prune_database_backups()'
