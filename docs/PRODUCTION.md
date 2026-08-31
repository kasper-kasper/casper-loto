# Production operations

The owner-authorized VPS runs PostgreSQL, FastAPI/scheduler, Telegram bot, Caddy,
Telegram Mini App and Web Admin with Docker Compose in `/opt/k-loto`. The existing
sslip.io HTTPS endpoint and VPS are sufficient; no extra host or domain is
required. Port 9443 is used because the VPS VPN owns the standard TLS ports.

Before every schema release, run `scripts/backup_production.sh` and verify a
non-empty PostgreSQL custom-format dump in the private backup volume. Deployment
then uploads the reviewed repository, runs `docker compose build` and starts the
stack. The API container applies Alembic and the idempotent production bootstrap
before serving traffic.

Production must define `MINIAPP_URL`, bot token, database credentials and Admin
credentials in ignored `/opt/k-loto/.env.production`. Caddy serves the Mini App
on `WEB_HOST` and Admin on `ADMIN_HOST`; `/api/*` proxies to FastAPI. PostgreSQL
is not published externally. Daily backups have 14-day retention.

After deployment verify container health, Alembic head, `/health`, both HTTPS
hosts, bot polling without conflicts, active lottery rows and jackpot balances.
Never print `.env.production` or Telegram tokens.
