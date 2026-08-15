# K-Loto

K-Loto is a virtual lottery platform that uses the in-game currency `CAS`. The
first version is a personal single-player installation, but user identity,
balances, tickets and audit records are designed as multi-user entities from
the beginning. No real money, payments, donations, cryptocurrency or cash-out
are part of this project.

Current version: **0.10.0 — Player Web**.

## Architecture

The project is a modular monolith. One backend owns business rules,
transactions and persistence; the Telegram bot, user Web client and Admin Panel are
separate adapters or clients.

The Telegram Mini App delivered in v0.6.0 is preserved but frozen. The active
player-interface roadmap is now: full Telegram bot gameplay, then a simple Web
version. The Admin Panel is a separate authenticated operational interface.

```text
k-loto/
|-- backend/
|   |-- src/k_loto/
|   |   |-- api/             # HTTP transport
|   |   |-- application/     # use cases
|   |   |-- domain/          # UI-independent rules
|   |   |-- infrastructure/  # database and external adapters
|   |   `-- core/            # configuration and logging
|   |-- migrations/          # Alembic migrations
|   `-- tests/
|-- bot/                     # aiogram player bot
|-- frontend/
|   |-- miniapp/             # preserved and frozen Telegram Mini App
|   |-- admin/               # independent Web Admin Panel
|   `-- web/                 # ordinary player browser client
|-- docs/
|-- infrastructure/
|-- scripts/
`-- docker-compose.yml
```

PostgreSQL is the source of truth. Scheduled timestamps are stored in UTC;
official draw rules and presentation use `Europe/Moscow`. All CAS amounts use
integers. The domain layer does not depend on Telegram, HTTP or React.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md),
[docs/SCHEDULER.md](docs/SCHEDULER.md),
[docs/TELEGRAM_BOT.md](docs/TELEGRAM_BOT.md),
[docs/ADMIN_PANEL.md](docs/ADMIN_PANEL.md),
[docs/WEB_APP.md](docs/WEB_APP.md) and
[docs/DEPLOYMENT_PLAN.md](docs/DEPLOYMENT_PLAN.md),
[docs/OPEN_DECISIONS.md](docs/OPEN_DECISIONS.md). Beginner-friendly browser and
tunnel setup is in [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md).

## Local development

Requirements:

- Python 3.12+
- PostgreSQL 16+
- Docker Compose (recommended)
- Node.js 22+ for web clients

Create local configuration:

```powershell
Copy-Item .env.example .env
```

Fill required values in `.env`; never commit it. For Docker, the PostgreSQL URL
hostname is `db`.

Start PostgreSQL, API and bot:

```powershell
docker compose up --build
```

The API is available at `http://localhost:8000`; `GET /health` reports API and
database status. The API performs startup draw reconciliation and runs the
periodic scheduler by default. Multiple invocations are protected by database
locks and idempotent settlement.

### Run without Docker

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn k_loto.main:app --reload
```

In a second terminal, run the player bot:

```powershell
.venv\Scripts\Activate.ps1
python -m bot
```

For a one-command local browser session after PostgreSQL and `.env` setup:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\enable_local_dev.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start_local_dev.ps1
```

The second command applies migrations, starts API and Mini App, creates the
ledgered test fixtures on first request and opens `http://127.0.0.1:5173`.
Production and Telegram authentication remain unchanged.

Alternatively, `uv sync --extra dev` installs the reproducible environment from
`uv.lock`.

## Migrations

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Migration `0001_domain_model` creates the core domain tables and database
immutability protections. Migration `0002_notification_outbox` adds durable,
immutable Telegram notification events. Migration `0003_web_accounts` adds
one-to-one password credentials for ordinary browser players.

## Checks and tests

```powershell
ruff check .
ruff format --check .
mypy backend/src
pytest
```

Lottery mathematics, settlement/recovery idempotency, Telegram authentication,
notification dispatch, preserved Mini App behavior, Admin security and player
Web sessions have focused tests. `scripts/check.ps1` runs all three frontend
test/build pipelines.

## Bot, frontend and admin

The aiogram bot is now the primary gameplay interface. It implements `/start`
and `/menu`, server-authoritative balance, Weekly 5/20 selection, random pick,
multi-ticket checkout, active/history tickets, results, player statistics and
durable purchase/result notifications. Daily remains read-only until its open
economics and cutoff decisions are resolved. The existing Mini App remains
available but frozen. The ordinary Web client supports Weekly purchase,
balance, active tickets, history and results.

Configure an existing Telegram player's Web login and run the local client:

```powershell
.venv\Scripts\python.exe -m scripts.configure_web_player
powershell -ExecutionPolicy Bypass -File .\scripts\start_web.ps1
```

Open `http://127.0.0.1:5175`. See [docs/WEB_APP.md](docs/WEB_APP.md).

Configure and run the independent Admin Panel:

```powershell
.venv\Scripts\python.exe -m scripts.configure_admin
powershell -ExecutionPolicy Bypass -File .\scripts\start_admin.ps1
```

Open `http://127.0.0.1:5174`. Balance and reserve changes always produce ledger
and audit records; completed draws have no edit API.

For the later permanent deployment, Admin will be served as a continuously
available HTTPS site: open its address and sign in, without manually starting
local processes. Backend, bot, player Web and Admin will be deployed together
after Daily is defined and implemented under the owner's current deployment
authorization.

## Secrets

Real credentials belong only in `.env` or a runtime secret store. Tokens,
passwords and connection strings must never appear in source, logs, README,
DEVLOG or CHANGELOG. Production deployment requires a separate owner command.
