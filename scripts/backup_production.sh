#!/bin/sh
set -eu

# Separate lock: maintenance takes this as well as the publication lock.
exec 9>/run/lock/k-loto-backup.lock
flock -x 9

cd /opt/k-loto
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "/backups/k-loto-'"$stamp"'.dump"'
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db \
  find /backups -type f -name 'k-loto-*.dump' -mtime +14 -delete
