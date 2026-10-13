# Casper Loto

Current release: **API 1.56.1 / Mini App 1.66.2 / Admin 1.60.0**.

The standalone browser client is retired in production (`/web`: HTTP 410;
`/api/v1/web`: HTTP 404). Its source remains in `frontend/web` for local use.
Production serves the Telegram Mini App and the separate Admin interface.

Casper Loto is a multi-user lottery platform with integer CAS accounting, an
immutable transaction ledger, recoverable draw scheduling, ten independent
draw lotteries and Kasper LIVE. Player interfaces are the Telegram bot and Telegram Mini App. The
administrator uses a separate HTTPS Web Admin Panel.

## Lotteries

Production currently has ten active lotteries. The authoritative human-readable
catalogue, including formats, schedules, prices, limits and prize categories, is
[docs/LOTTERIES.md](docs/LOTTERIES.md).

Each entity owns independent draw numbers, ticket numbers, jackpot,
central Kasper Fund. Empty draws are settled normally. Every active
Telegram player receives one idempotent result message and a purchase button.

## Repository

- `backend/` — FastAPI, domain/application services, bot, scheduler and Alembic;
- `frontend/miniapp/` — primary premium blue/red/gold player interface;
- `frontend/admin/` — separate administrator website;
- `infrastructure/` — HTTPS gateway configuration;
- `scripts/` — checks, backups, bootstrap and local operations;
- `docs/` — architecture, rules and operations.

## Local checks

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

The command runs Ruff, mypy, pytest and both active frontend suites/builds.
Secrets belong only in ignored `.env` files.

See [architecture](docs/ARCHITECTURE.md), [Daily rules](docs/DAILY_CORE.md),
[Telegram](docs/TELEGRAM_BOT.md) and [production operations](docs/PRODUCTION.md).
The owner-facing development order is maintained in the Russian
[next-steps plan](docs/NEXT_STEPS.md).
