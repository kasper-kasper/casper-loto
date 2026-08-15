# Permanent deployment plan

The owner-authorized production deployment was completed in v0.12.0. Operational
details are in `PRODUCTION.md`; this file retains the release topology and
rollback policy.

## Owner experience

- Admin Panel: open its HTTPS address, enter username/password, work normally.
- Player Web: press the one-click Web button in the private bot chat; an optional
  provisioned login/password remains a fallback.
- Telegram bot: remains online continuously and restarts automatically.
- No owner-facing `npm`, `uvicorn`, tunnel or PowerShell command is required for
  ordinary use.

## Target topology

```text
Internet / Telegram
        |
        v
HTTPS reverse proxy
   |         |
   |         +-- compiled Admin static site
   +------------ compiled player Web static site
   +------------ /api -> FastAPI

private service network
   |-- FastAPI + scheduler
   |-- one aiogram polling bot + notification outbox worker
   `-- PostgreSQL (not publicly exposed)
```

The reverse proxy owns TLS and routes same-origin API requests. Admin
credentials, Telegram tokens and database credentials stay in a server-side
secret environment and never enter JavaScript bundles. Services use automatic
restart and health checks; migrations run before new application processes
become active.

## Release sequence

1. build immutable backend, Admin and player Web artifacts;
2. back up PostgreSQL;
3. run Alembic migrations once;
4. start/replace API, scheduler and bot services;
5. publish versioned static assets;
6. verify database/API/bot/scheduler/Admin health;
7. retain the previous application artifact for rollback without rolling back
   immutable business data.

No production connection or deployment is authorized by this plan itself.
