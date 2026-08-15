# Production operation

K-Loto runs on the owner-authorized VPS as one Docker Compose project in
`/opt/k-loto`:

- PostgreSQL 16 on a private Docker network and persistent volume;
- FastAPI with the scheduler and startup recovery;
- one aiogram polling bot and notification outbox worker;
- Caddy serving compiled player Web and Admin sites with automatic HTTPS.

The server's existing VPN owns ports 443 and 8443 and is intentionally left
untouched. K-Loto uses public HTTPS port 9443 and port 80 only for automatic
certificate management. Free `sslip.io` hostnames point to the VPS, so no paid
domain is required.

All containers use `restart: unless-stopped`. Database, Caddy certificates and
backups use named persistent volumes. PostgreSQL is not published to the
internet. Runtime credentials are stored only in server `.env.production` with
mode 0600 and in the owner's ignored local `.env`.

## Backup

`scripts/backup_production.sh` creates a compressed PostgreSQL custom-format
dump in the private backup volume and removes dumps older than 14 days. The VPS
runs it daily from `/etc/cron.d/k-loto-backup`. A release should also take a
backup before schema migration once business data exists.

## Player setup

1. Player sends `/start` to the production Telegram bot.
2. Owner signs into Admin, opens Players and credits CAS with a mandatory reason.
3. Owner configures Weekly/Daily price, base jackpot and reserve as needed.
4. Player presses **🌐 Открыть Web-версию** in the bot and follows the one-time
   login button. No Web password or Admin provisioning is required.
5. Player buys through Telegram or the already authenticated player Web site.

Admin may still create a username/password in the Players card as a fallback.

The initial Admin password exists only in the owner's ignored `.env` under
`ADMIN_INITIAL_PASSWORD`. It is never committed or sent to DevLog.
