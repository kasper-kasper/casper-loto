# Production storage maintenance

Read-only audit: 2026-10-04. Filesystem: 40 GB total, about 14 GB used and
25 GB available (36% used). This is a point-in-time measurement.

| Mechanism | Trigger | Scope |
| --- | --- | --- |
| Database backup retention | Every day, 03:30 MSK, `/etc/cron.d/k-loto-backup` | Creates a PostgreSQL dump, then removes only `/backups/k-loto-*.dump` older than 14 days. |
| System temporary files | Active `systemd-tmpfiles-clean.timer` | OS temporary-file policies. |
| System log rotation | Active `logrotate.timer` | Configured OS logs; this is not a Docker container log limit. |
| System journal | `SystemMaxUse=1G` | Journald storage cap; measured 992.5 MB. |
| Docker build cache | After successful general `scripts/release_vps.py` deployment | Prunes build cache while retaining 2 GB. No separate scheduled job found. |
| Old Docker images | After successful general deployment | Removes unused K-Loto-labelled images older than 48 hours. No volume pruning. |

Docker API, bot and gateway containers currently use `json-file` logging
with an empty options map, so no explicit size/rotation limit is configured.
The audit found no universal or scheduled K-Loto Docker cleanup process.
Targeted Mini App publication scripts do not perform the general release
script's Docker pruning stages.

Measured Docker usage: images 3.52 GB (1.717 GB reclaimable), build cache
2.035 GB, volumes 2.554 GB. Running containers and database storage are not
garbage and must not be removed. Release rollback archives in the project
backup directory are separate from the database dump retention policy.

No maintenance configuration was changed by this audit.
