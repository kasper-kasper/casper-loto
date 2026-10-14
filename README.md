# Casper Loto

Current release: **API 1.56.3 / Mini App 1.66.4 / Admin 1.60.2**.

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
central Kasper Fund. Empty draws are settled normally. Result messages respect
current consent. An uncertain Telegram acknowledgement requires review and is
never automatically resent.

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

Install Python dependencies with `uv sync --locked --extra dev`; production uses
`uv sync --locked --no-dev --no-editable` and verifies actual installed versions.
Client checks build fresh copies with `npm ci`; Web sources are not required.
For a new PostgreSQL database use `python -m scripts.migrate_database`.
Release from a clean commit with `python -m scripts.release_vps`; use
`--reuse-built` only for builds whose source/artifact hashes still verify.

See [audit step 5](docs/AUDIT_STEP5.md) and
[audit results and remaining work](docs/AUDIT_RESULTS_2026-10-14.md).

See [architecture](docs/ARCHITECTURE.md), [Daily rules](docs/DAILY_CORE.md),
[Telegram](docs/TELEGRAM_BOT.md) and [production operations](docs/PRODUCTION.md).
The owner-facing development order is maintained in the Russian
[next-steps plan](docs/NEXT_STEPS.md).
