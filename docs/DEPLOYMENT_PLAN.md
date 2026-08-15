# Permanent deployment plan

Deployment remains a later stage after Daily rules and code are complete. The
simple player Web client is ready for this owner-authorized target.

## Owner experience

- Admin Panel: open its HTTPS address, enter username/password, work normally.
- Player Web: open its HTTPS address and enter the provisioned login/password.
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

The reverse proxy will own TLS and route same-origin API requests. Admin
credentials, Telegram tokens and database credentials stay in a server-side
secret environment and never enter JavaScript bundles. Services use automatic
restart and health checks; migrations run as an explicit release step before
new application processes become active.

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
