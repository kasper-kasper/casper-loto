# K-Loto

Current version: **0.15.0 — Mini App First**.

K-Loto is a multi-user lottery platform with integer CAS accounting, an
immutable transaction ledger, recoverable draw scheduling and four independent
lotteries. Player interfaces are the Telegram bot and Telegram Mini App. The
administrator uses a separate HTTPS Web Admin Panel. The former ordinary player
Web client was retired in v0.14.0.

## Lotteries

| Code | Name | Format | Moscow draw time | Cutoff |
|---|---|---:|---:|---:|
| `weekly` | ЛСД-лото | 5/20 | Sunday 20:00 | 5 min |
| `pll` | ПЛЛ-лото | 4/15 | daily 02:22 | 2 min |
| `pss` | ПСС-Лото | 4/15 | daily 12:00 | 2 min |
| `khan` | ХАН-Лото | 4/15 | daily 18:00 | 2 min |

Each entity owns independent draw numbers, ticket numbers, jackpot,
distribution fund and reserve. Empty draws are settled normally. Every active
Telegram player receives one idempotent result message and a purchase button.

## Repository

- `backend/` — FastAPI, domain/application services, bot, scheduler and Alembic;
- `frontend/miniapp/` — primary premium blue/red/gold player interface;
- `frontend/admin/` — separate administrator website;
- `infrastructure/` — HTTPS gateway configuration;
- `scripts/` — checks, backups, bootstrap and DevLog tooling;
- `docs/` — architecture, rules and operations.

## Local checks

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

The command runs Ruff, mypy, pytest and both active frontend suites/builds.
Secrets belong only in ignored `.env` files.

See [architecture](docs/ARCHITECTURE.md), [Daily rules](docs/DAILY_CORE.md),
[Telegram](docs/TELEGRAM_BOT.md) and [production operations](docs/PRODUCTION.md).
