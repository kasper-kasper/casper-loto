# K-Loto

K-Loto is a virtual lottery platform that uses the in-game currency `CAS`. The
first version is a personal single-player installation, but user identity,
balances, tickets and audit records are designed as multi-user entities from
the beginning. No real money, payments, donations, cryptocurrency or cash-out
are part of this project.

Current version: **0.5.0 — Milestone 4 / Telegram Bot**.

## Architecture

The project is a modular monolith. One backend owns business rules,
transactions and persistence; the Telegram bot, Mini App and Admin Panel are
separate adapters or clients.

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
|   |-- miniapp/             # future Telegram Mini App
|   `-- admin/               # future independent web admin
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
[docs/TELEGRAM_BOT.md](docs/TELEGRAM_BOT.md) and
[docs/OPEN_DECISIONS.md](docs/OPEN_DECISIONS.md).

## Local development

Requirements:

- Python 3.12+
- PostgreSQL 16+
- Docker Compose (recommended)
- Node.js 22+ for later frontend milestones

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

Alternatively, `uv sync --extra dev` installs the reproducible environment from
`uv.lock`.

## Migrations

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Migration `0001_domain_model` creates the core domain tables and database
immutability protections. Migration `0002_notification_outbox` adds durable,
immutable Telegram notification events.

## Checks and tests

```powershell
ruff check .
ruff format --check .
mypy backend/src
pytest
```

Lottery mathematics, settlement/recovery idempotency, notification formatting
and dispatch behavior have focused tests.

## Bot, frontend and admin

The aiogram bot implements `/start`, Telegram identity binding and durable
purchase/result notifications. It deliberately has no purchase buttons;
checkout belongs to the future Mini App. Neither frontend may determine
balances, prices, draw assignment or payouts.

## Secrets

Real credentials belong only in `.env` or a runtime secret store. Tokens,
passwords and connection strings must never appear in source, logs, README,
DEVLOG or CHANGELOG. Production deployment requires a separate owner command.
