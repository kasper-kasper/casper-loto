# Production storage maintenance

Small-project profile, approved 2026-10-04 for fewer than 50 players. Cleanup
is centralized in `scripts/server_maintenance.py`. Retention settings live in
`infrastructure/server-maintenance.toml` and need no database migration.

| Data | Retention / limit |
| --- | --- |
| Financial ledger, balance movements, purchased tickets, draws and database audit records | Permanent. Maintenance never queries, modifies or deletes business rows or Docker volumes. |
| API and bot diagnostic logs | Private gzip archives for 90 days; capture hourly, before cleanup and before service recreation. Also retain the newest three archives per service. |
| API and bot local Docker log buffer | 20 MB × 5 files per service (100 MB each). |
| Gateway and PostgreSQL diagnostic buffer | 10 MB × 3 files per service (30 MB each). |
| Database backup dumps | Daily at 03:30 MSK; existing retention of 14 days. These are copies, not expiration of database history. |
| Docker build cache | Target reserve 512 MB; only unused entries older than 48 hours are eligible. Recent cache can temporarily exceed the reserve. |
| Project Docker images | Keep current/referenced images and two most recent tagged rollback versions per repository; other eligible project images expire after seven days. |
| Known release rollback archives | Keep newest three per category and everything younger than 14 days. |
| Known uploaded release tarballs in `/tmp` | Delete after 48 hours. Unknown files, dumps, directories, symlinks and hardlinks are excluded. |
| OS journal and temporary files | Existing journald 1 GB cap, logrotate and systemd-tmpfiles policies. |

Cleanup runs daily at 05:00 MSK with up to five minutes of jitter through
`k-loto-maintenance.timer`. Hourly preservation uses `k-loto-log-archive.timer`
and the same script. Both acquire the publication and backup locks. Cleanup
skips active backups/publications, unhealthy services and recent upload activity.
It never runs Docker system/volume pruning or truncates Docker's own log files.

Diagnostic archives and cursor state live under `/opt/k-loto/.maintenance`
(directories 0700, files 0600). Log contents are not echoed to deployment output.
The cursor advances only after successful capture; failed capture stops cleanup.
A new container identity triggers collection of all available new-container logs.
Capture copies Docker's available buffer: an unusual burst exceeding 100 MB
between captures, prolonged timer failure, or uncoordinated container removal
can lose diagnostic lines. The permanent database ledger remains authoritative
for balances and lottery history.

Publications must hold `scripts.vps_operation_lock.remote_operations_lock`
through backup/upload/build/restart/health and call `archive_diagnostic_logs()`
under that lock before API/bot recreation. `scripts/release_vps.py` does both.
Historical one-off publication scripts are not the supported future release path.

## Inspection and tuning

Run from `/opt/k-loto` as root:

```sh
python3 scripts/server_maintenance.py             # read-only plan
python3 scripts/server_maintenance.py --apply     # cleanup with health checks
python3 scripts/server_maintenance.py --archive-logs
systemctl list-timers 'k-loto-*'
systemctl status k-loto-maintenance.service k-loto-log-archive.service
cat .maintenance/last-run.json
```

The latest cleanup report records freed space, removed paths/images, health
and a warning flag at 80% filesystem usage. It does not send notifications.
Failed service runs remain visible in systemd/journald.

**When to increase limits:** if frequent releases rebuild old layers, raise
`cache_keep_mb` to 1024 or 2048. If diagnostics approach the 100 MB per-hour
buffer, capture more frequently or increase the API/bot Compose log buffer
(requires recreation after capture). Review compressed-log disk growth before
extending the 90-day retention. At 80% usage, investigate growth; do not shorten
financial history or delete volumes. Player count alone is not a tuning signal.

Initial read-only audit (2026-10-04): 40 GB filesystem, about 14 GB used,
24–25 GB available. Build cache was about 2 GB; Docker logs had no explicit
limits. This is a historical measurement, not a guaranteed current value.


## Audit correction, 2026-10-11

The same rollback archive policy now covers both `/opt/k-loto/backups` and
`/opt/k-loto-backups`, including the known Halloween/Grand/Aurora/Vault/
distribution/performance release families and their documented audit copies.
The source-release family retains three newest archives together; younger than
14 days always survives. Unknown names remain untouched. All `before-<feature>`
image tags participate in protection of the two newest rollback versions.
Legacy untagged images explicitly labelled `com.docker.compose.project=k-loto`
are eligible after seven days even when the old gateway build omitted its
service label. New prebuilt gateway images include the service label.

At audit time the 40 GB filesystem was 89% full, with 4.2 GB available.
Most release copies were younger than seven days; retention is deliberately not
shortened to reclaim those. If growth continues after normal expiry, increase
VPS disk capacity. Financial history is never a storage-cleanup target.
