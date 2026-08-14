# K-Loto

K-Loto is a virtual lottery platform that uses the in-game currency `CAS`. The
first version is a personal single-player installation, but user identity,
balances, tickets and audit records are designed as multi-user entities from
the beginning. No real money, payments, donations, cryptocurrency or cash-out
are part of this project.

Current version: **0.1.0 — Milestone 0 / Foundation**.

## Architecture

The project starts as a modular monolith. One backend owns the business rules,
transactions and persistence; the Telegram bot, Mini App and Admin Panel are
separate adapters/clients of that backend.

```text
k-loto/
|-- backend/
|   |-- src/k_loto/
|   |   |-- api/             # HTTP transport
|   |   |-- application/     # use cases (from Milestone 1)
|   |   |-- domain/          # UI-independent rules (from Milestone 1)
|   |   |-- infrastructure/  # database and external adapters
|   |   `-- core/            # configuration and logging
|   |-- migrations/          # Alembic migrations
|   `-- tests/
|-- bot/                     # aiogram player bot (Milestone 4)
|-- frontend/
|   |-- miniapp/             # Telegram Mini App (Milestone 5)
|   `-- admin/               # independent web admin (Milestone 6)
|-- docs/
|-- infrastructure/
|-- scripts/
`-- docker-compose.yml
```

PostgreSQL is the source of truth. Scheduled timestamps are stored in UTC;
official draw rules and presentation use `Europe/Moscow`. All CAS amounts use
integers. The domain layer must not depend on Telegram, HTTP or React.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for boundaries and known risk
areas, and [docs/OPEN_DECISIONS.md](docs/OPEN_DECISIONS.md) for unresolved
business parameters.

## Local development

Requirements:

- Python 3.12+
- PostgreSQL 16+
- Docker Compose (recommended)
- Node.js 22+ will be needed when frontend milestones start

Create local configuration:

```powershell
Copy-Item .env.example .env
```

Fill all required values in `.env`. Do not commit it. For Docker, use a
PostgreSQL URL whose hostname is `db`, for example a URL in the form
`postgresql+asyncpg://<user>:<password>@db:5432/<database>`.

Start PostgreSQL and the API:

```powershell
docker compose up --build
```

The API is available at `http://localhost:8000`; health information is exposed
at `GET /health` and includes application and database status.

### Run without Docker

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn k_loto.main:app --reload
```

`backend/src` is configured as the package source by `pyproject.toml`.
Alternatively, `uv sync --extra dev` installs the reproducible environment from
the committed `uv.lock` file.

## Migrations

Create and apply migrations from the repository root:

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Every schema change must include a migration. Milestone 0 contains only the
migration framework; domain tables arrive in Milestone 1.

## Checks and tests

```powershell
ruff check .
ruff format --check .
mypy backend/src
pytest
```

Lottery mathematics, settlement idempotency and recovery will receive focused
tests in the relevant milestones.

## Frontend, bot and admin

The client directories currently document their boundaries only. They are not
scaffolded yet because their implementation belongs to Milestones 4–6:

- `bot` will use aiogram 3.x and call backend application/API boundaries;
- `frontend/miniapp` will use React, TypeScript, Vite and validated Telegram
  Mini App `initData`;
- `frontend/admin` will be a separately authenticated React application.

Neither frontend may determine balances, prices, draw assignment or payouts.

## Secrets

Real credentials belong only in `.env` or the production secret store. Tokens,
passwords and connection strings must never appear in source, logs, README,
DEVLOG or CHANGELOG. Production deployment is deliberately not included in
Milestone 0 and requires a separate owner command.
