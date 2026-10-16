# Production storage maintenance

## Backup supervision (2026-10-16)

`k-loto-backup.timer` runs at 03:30 Europe/Moscow with `Persistent=true`:
systemd starts a missed run after the VPS returns. The native oneshot invokes
`/bin/sh` explicitly, takes the operations lock, and then the existing backup
lock. It replaces the old `/etc/cron.d/k-loto-backup` entry, which failed with
exit 126 because the script was not executable. Source promotion does not need
to preserve executable bits for this path to work.

The independent host watchdog checks the verified backup volume every minute.
Missing, empty, future-dated or older-than-26-hour copies do not count as fresh.
A failed backup service is reported even if an earlier backup is still fresh.
Private Telegram alerts use the existing bot token and explicit owner ID from
`.env.production`, without depending on API/DB availability. One message is sent
per incident and one when all monitored conditions recover. The watchdog also
reports service/public-health failures and independent scheduler/delivery/disk
warnings; its own warning feedback is excluded.

Notification state lives privately in `.maintenance/owner-health-alert.json`.
Definitive Telegram rejections retry after a delay (respecting HTTP 429).
An ambiguous timeout is recorded as `uncertain` and is not blindly replayed;
inspect `owner_notification` in `.monitoring/state.json` if delivery is uncertain
or unavailable. Tokens and recipient IDs are never written to that public state.
Initial healthy checks send no message. A host watchdog cannot notify while the
entire VPS is powered off; that requires a separately hosted uptime monitor.

```sh
systemctl status k-loto-backup.timer k-loto-backup.service
systemctl show k-loto-backup.timer -p Persistent -p NextElapseUSecRealtime
journalctl -u k-loto-backup.service --since yesterday
cat /opt/k-loto/.monitoring/state.json
```

For a full restore check, run `scripts/verify_backup_restore.sh` inside the DB
container with the selected `/backups/k-loto-*.dump` path. It creates a unique
disposable database, restores the complete archive, checks all five account
families against the immutable ledger and checks index validity, then drops only
its own database. Production rows are not changed. This is an on-demand check,
not a daily restore job.

Production verification on 2026-10-16: the native systemd job succeeded and
created `k-loto-20261016T170612Z.dump` (82,807,696 bytes). A complete isolated
restore through schema `0056_player_profile_projection` recovered 697,652
tickets and 342,355 ledger records; all five account/ledger families and indexes
passed verification. The disposable database was removed. Seven backups remain,
the owner received the setup notification, and the watchdog has no warnings.

Small-project profile, approved 2026-10-04 for fewer than 50 players. Cleanup
is centralized in `scripts/server_maintenance.py`. Retention settings live in
`infrastructure/server-maintenance.toml` and need no database migration.

| Data | Retention / limit |
| --- | --- |
| Financial ledger, balance movements, purchased tickets, draws and database audit records | Permanent. Maintenance never queries, modifies or deletes business rows or Docker volumes. |
| API and bot diagnostic logs | Private gzip archives for 90 days; capture hourly, before cleanup and before service recreation. Also retain the newest three archives per service. |
| API and bot local Docker log buffer | 20 MB × 5 files per service (100 MB each). |
| Gateway and PostgreSQL diagnostic buffer | 10 MB × 3 files per service (30 MB each). |
| Database backup dumps | At most seven newest validated dumps in the backup volume, counting both daily and pre-release copies. Nightly creation at 03:30 MSK; prune after successful creation and during daily maintenance. Failed/incomplete dumps do not replace recovery points. |
| Docker build cache | Target reserve 512 MB of unused cache, without an age exemption. Docker may retain cache required by active builds/images; this is a pruning target, not a guaranteed hard quota. |
| Project Docker images | Keep current/referenced images and two most recent tagged rollback versions per repository; other eligible project images expire immediately regardless of age. Recheck tags, ownership and container references before removal. Required intermediate parent images/layers remain protected by Docker; they are not additional release versions. |
| Known release rollback archives | Keep only the newest three per category across both archive directories combined; remove older copies regardless of age. Owner-approved 2026-10-11. |
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

The database count is seven files, not seven calendar days: frequent pre-release
backups can shorten the time window. Backup creation writes a `.partial` file,
checks its archive table of contents with `pg_restore --list`, then atomically
renames it. Before pruning, the retained dumps' tables of contents are checked.
This detects unreadable metadata, not all possible restore errors; periodically
perform a complete restore to an isolated disposable database. Count-based
retention only touches the verified `k-loto_backups` volume and recognized dump
names; it never deletes a Docker volume or touches `k-loto_postgres_data`.
The owner chose server-only storage; no computer transfer is configured here.
Copies on the same VPS do not protect against loss of that VPS.

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
The source-release family retains three newest archives together. The owner's
follow-up decision removes the former 14-day protection: `archive_min_age_days=0`,
with three copies per category shared across both directories. The fourth and
older copies are eligible even if created today. Unknown names remain untouched.
All `before-<feature>`
image tags participate in protection of the two newest rollback versions.
Legacy untagged images explicitly labelled `com.docker.compose.project=k-loto`
are eligible after seven days even when the old gateway build omitted its
service label. New prebuilt gateway images include the service label.

At audit time the 40 GB filesystem was 89% full, with 4.2 GB available.
This historical measurement preceded the owner's count-only retention decision.
If growth continues after cleanup, increase VPS disk capacity. Financial history
is never a storage-cleanup target. The later owner-approved compact policy
replaces database retention with seven newest files and image age protection
with count-only retention; diagnostic logs retain their separate 90-day policy.


The first extended sweep reclaimed 847,052,800 bytes (about 0.85 GB); health
passed and free space rose from about 4.2 to 5.0 GiB before release backups.
Its conservative per-image ownership/protection checks exceeded ten minutes.
The service timeout is therefore 30 minutes; each Docker command still has its
own bounded timeout and the shared operations/backup locks remain held.
The temporary SSH observer timed out at ten minutes, but the server completed
and persisted the successful report; no concurrent publication was allowed.

## Count-only retention applied, 2026-10-11

The approved policy was published and applied with both maintenance locks.
Thirty surplus known archives were removed, reclaiming 2,142,216,192 bytes
(about 2.14 GB). Filesystem usage fell from 92% to 87%; available space rose
from 3.2 to 5.2 GiB. Each known category has at most three copies across both
directories; retained files match the three newest copies captured before cleanup.
All 18 files outside the known archive allowlist retained their size, timestamp
and inode. No Docker images were removed in this sweep. Seventeen maintenance
regressions passed on Linux, including the symlink safety case; scoped Ruff passed.
HTTPS/API/database health passed and both maintenance timers remain active.
The 80% disk warning remains set, so capacity should still be monitored.

## Compact policy applied, 2026-10-11

Owner approved server-only storage: seven newest database dumps, current plus
two prior tagged release versions per project service, and a 512 MB unused-cache
target without age exemptions. Backup creation and a full restore into a unique
disposable database passed; the temporary database was removed.

Cleanup reclaimed 18,223,230,976 bytes (18.22 GB). `df -h` changed from 87% used /
5.2 GiB available to 41% used / about 23 GiB available (rounded display).
The seven retained dumps occupy 480,327,645 bytes; nine tagged release images
remain across API/bot/gateway. Docker's unused build cache is 382.6 MB. Required
intermediate/base images are not additional release versions; `docker system df`
also lists images belonging to other services. Do not equate all image metadata
entries with standalone rollback copies or add shared layer/cache sizes together.

All running container IDs/images and protected rollback IDs were preserved.
Unknown archive files retained their metadata, project health and timers passed.
Backend: 523 passed and one Windows-only symlink skip, subsequently passed within
26 Linux maintenance checks; Ruff, mypy and Linux backup-shell syntax passed.
Read-only post-cleanup checks found zero balance/ledger mismatches, zero scheduled
draws overdue by ten minutes and zero invalid indexes. No app services restarted.
