# K-Loto

Current version: **1.6.0 — «ГРОБ» 3/16**.

K-Loto is a multi-user lottery platform with integer CAS accounting, an
immutable transaction ledger, recoverable draw scheduling and six independent
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
| `september` | 3 СЕНТЯБРЯ | 3/33 | daily 03:33 and 15:33 | 2 min |
| `grob` | ГРОБ | 3/16 | daily 06:06 and 23:06 | 2 min |

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
