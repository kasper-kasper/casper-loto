# Development log

## [0.8.0] - 2026-08-15

### Milestone 6 — Web Admin Panel

Implemented the independent administrative control surface and updated the
product roadmap after the owner froze Telegram Mini App development.

Done:

- added Argon2 login with signed short-lived HttpOnly SameSite sessions;
- added per-session CSRF validation to every administrator mutation;
- added a stable database administrator identity for permanent audit records;
- added system dashboard, players, lotteries/funds and recent activity queries;
- balance and reserve target changes use locked, idempotent ledger transactions
  plus audit records in the same database transaction;
- ticket price and base jackpot configuration requires a reason and creates an
  audit record; Weekly price remains divisible by four for integer payouts;
- added filterable ledger, immutable draw details, ticket/payout archive and
  calculated number statistics;
- created the standalone technical dark-theme React/TypeScript Admin Panel;
- added a credential configurator that writes secrets only to ignored `.env`;
- expanded the standard check script to both frontend applications;
- documented the frozen Mini App and the new Bot → user Web roadmap.

System behavior:

- administrators can trace players, funds, draws and every CAS movement;
- player balance and lottery reserve cannot be overwritten without ledger and
  audit history;
- current jackpot/distribution values remain lifecycle-owned and read-only;
- completed draws remain immutable and expose no write route;
- number intelligence is rebuilt from immutable draw history, not trusted as a
  separate source of truth;
- incomplete administrator credentials disable login safely.

Technical:

- version: 0.8.0;
- migration: no schema change; existing `admin_audit_log` and ledger are used;
- backend: 39 typed source files, 87 pytest tests;
- frontend: 8 Mini App Vitest tests + 4 Admin Vitest tests;
- security: Argon2, HMAC-SHA256 session, HttpOnly/SameSite cookie, Secure in
  production, CSRF token, row locks and idempotency keys;
- browser visual inspection was unavailable because no browser runtime was
  connected; Admin DOM/component tests and production build passed;
- local PostgreSQL integration remains unavailable on this machine; no VPS
  connection was attempted.

Known:

- schedule and payout editing remain locked while Daily cutoff/economics are open;
- production reverse proxy, rate limiting and deployment remain later work;
- Telegram Mini App code is intentionally preserved at v0.7.0 and frozen.

## [0.7.0] - 2026-08-15

### Local Development & Test Mode

Added a playable ordinary-browser workflow before Milestone 6 without weakening
Telegram or production authentication.

Done:

- added a signed local browser session stored in an HttpOnly SameSite cookie;
- restricted session issue/use to development, loopback client, Host and Origin;
- added idempotent `Local Test Player`, Weekly/Daily fixtures and future draws;
- initial user balance, jackpot and reserve are credited through immutable
  ledger entries;
- added a local-only `+ TEST CAS` refill, also recorded through ledger;
- added one-command enable/start scripts and automatic browser launch;
- added an isolated `dev:telegram` frontend mode and Cloudflare Quick Tunnel
  helper that refuses to run while browser bypass is enabled;
- documented PostgreSQL setup and beginner workflows.

System behavior:

- browser testing needs neither Telegram nor a domain;
- the first browser request creates playable local fixtures exactly once;
- restarting does not duplicate the player, lotteries or initial CAS credits;
- Telegram tunnel testing uses real signed `initData`, never the local cookie;
- `APP_ENV=production` makes the development session endpoint unavailable even
  if its enable flag is accidentally set.

Technical:

- migration: no schema change after `0002_notification_outbox`;
- backend: 36 typed source files, 78 pytest tests;
- frontend: 8 Vitest tests, TypeScript, ESLint and production build;
- tunnel: official `cloudflared` Quick Tunnel download/run helper;
- local PostgreSQL integration was not executed because PostgreSQL/Docker is not
  installed on this machine; no VPS connection was attempted.

Known:

- PostgreSQL 16+ remains a one-time local prerequisite;
- temporary tunnel URLs change after restart and must be copied to `MINIAPP_URL`.

## [0.6.0] - 2026-08-15

### Milestone 5 — Telegram Mini App

Implemented the authenticated player Mini App and its backend read/purchase API.

Done:

- created a mobile-first React, TypeScript and Vite application;
- added dashboard balance, Weekly/Daily cards, jackpot and Moscow countdowns;
- added Weekly 5/20 picker, Web Crypto random pick and accessible number states;
- added single purchase, duplicate combinations and atomic multi-ticket cart;
- added active tickets, history, matches, prizes and recent results;
- added Telegram `initData` HMAC/age validation and user binding on every API
  request;
- added a configurable `/start` Web App launch button;
- purchases after 19:55 now prepare and use the next Weekly draw under the
  existing lottery lock.

System behavior:

- price, balance and draw assignment come only from the backend;
- changed, expired, malformed and future-dated Telegram authentication is
  rejected before database access;
- Daily is visible but cannot be purchased until its payout model is resolved;
- cart persistence has no guessed TTL: without owner configuration it stays in
  memory for the current session, while configured storage expires strictly;
- checkout retries use client-generated idempotency keys and the existing
  server ledger protections.

Technical:

- migration: no schema change after `0002_notification_outbox`;
- backend: 34 typed source files, 67 pytest tests;
- frontend: 7 Vitest tests, TypeScript, ESLint and Vite production build;
- dependencies: React 19, TypeScript 5.9, Vite 7;
- local in-app browser visual inspection was unavailable because no browser
  runtime was connected; component tests and production build passed;
- live `alembic check` remains unavailable without local PostgreSQL and no VPS
  connection was attempted.

Known:

- OD-007 exact cart TTL and OD-008 final visual design remain owner decisions;
- Python 3.14 continues to expose pytest-asyncio deprecation warnings.

## [0.5.0] - 2026-08-14

### Milestone 4 — Telegram Bot

Implemented the player Telegram adapter and durable notification delivery.

Done:

- `/start` idempotently binds a Telegram identity and creates a zero-CAS
  balance when needed;
- the bot shows the current balance and directs purchases to the future Mini
  App without exposing ordinary Telegram purchase buttons;
- each committed checkout creates one purchase notification for the complete
  single- or multi-ticket order;
- each committed Weekly settlement creates one result notification per player,
  including all tickets, matches, prizes and zero-win results;
- an outbox worker claims events concurrently, retries failures with backoff and
  recovers stale processing locks;
- unique event keys and terminal sent records prevent routine repeat delivery.

System behavior:

- Telegram outages do not roll back or repeat tickets, ledger entries, payouts
  or completed draws;
- an idempotent business retry cannot create a second notification event;
- notification payload/history is immutable at the PostgreSQL layer;
- only redacted failure codes are persisted.

Technical:

- migration: `0002_notification_outbox`;
- dependency: aiogram 3.x;
- tests cover identity binding, Russian message formatting, multi-ticket
  payloads, result payloads, one-time dispatch and redacted failure handling;
- Ruff and formatting passed;
- strict mypy passed for 31 source files;
- pytest: 58 passed;
- Alembic head and offline PostgreSQL upgrade generation passed;
- live `alembic check` was not run because no local PostgreSQL is installed and
  the project must not connect to the configured VPS during development.

Known:

- Telegram Bot API has no caller idempotency key; a process crash after Telegram
  accepts a message but before `SENT` commits may repeat that message, without
  repeating any business operation;
- pytest-asyncio emits Python 3.14 deprecation warnings in the current toolchain.

## [0.4.0] - 2026-08-14

### Milestone 3 — Scheduler & Recovery

Implemented explicit Moscow schedules, automatic draw preparation and
chronological startup/periodic recovery.

Done:

- Weekly runs Sunday 20:00 MSK and closes sales at 19:55;
- Daily schedule generation uses confirmed 02:22 and 18:00 slots;
- the first draw is the nearest future slot and is never backfilled before the
  system's first start;
- after each Weekly settlement the next numbered draw is prepared;
- startup reconciliation repeatedly settles overdue Weekly draws oldest first;
- APScheduler invokes the same idempotent reconciliation every configured
  interval.

System behavior:

- downtime does not discard a draw or change its official `scheduled_at`;
- `executed_at` records delayed technical execution;
- repeated scheduler processes cannot create a second pending draw because the
  lottery counter row is locked;
- repeated settlement returns the completed result without a second payout;
- Daily payout/settlement remains disabled until its payout model is decided.

Technical:

- migration: no schema change after `0001_domain_model`;
- dependency: APScheduler 3.11;
- tests cover Weekly/Daily boundaries, cutoff, draw numbering, duplicate
  preparation and chronological multi-draw recovery.
- Ruff and formatting passed;
- strict mypy passed for 26 source files;
- pytest: 51 passed;
- Alembic head and offline PostgreSQL upgrade generation passed;
- live `alembic check` was not run because no local PostgreSQL is installed and
  the project must not connect to the configured VPS during development.

## [0.3.0] - 2026-08-14

### Milestone 2 — Weekly Core

Implemented the complete Weekly 5/20 domain mathematics and transactional
application services.

Done:

- canonical ticket validation and atomic multi-ticket purchase;
- duplicate combinations remain valid independent tickets;
- backend chooses the first draw still open for sales;
- one transaction updates balance, ticket numbering, draw totals, jackpot,
  distribution fund and three balancing ledger records;
- official numbers use `secrets.SystemRandom`;
- categories 0/5 through 5/5, reserve fallback and both carryovers;
- completed draw retry returns the existing result without new payouts;
- empty draws receive official numbers and complete normally.

System behavior:

- Weekly prices must be divisible by 4 CAS so 25% prizes are exact integers;
- indivisible equal-split remainders are assigned deterministically by ascending
  public ticket number;
- insufficient reserve aborts the atomic settlement for later retry, without
  using jackpot or creating CAS;
- a won jackpot is fully paid and then receives a ledgered base-jackpot reset.

Technical:

- no schema migration was required after `0001_domain_model`;
- row locks serialize lottery counters, accounts and draw settlement;
- purchase keys are checked both before and after the lottery lock to prevent
  concurrent duplicate checkout;
- Ruff and formatting passed;
- strict mypy passed for 23 source files;
- pytest: 42 passed.

Known:

- PostgreSQL integration tests still require a local Docker/PostgreSQL runtime;
- Python 3.14 causes third-party pytest-asyncio deprecation warnings.

## [0.2.0] - 2026-08-14

### Telegram DevLog integration

Added secret-safe local tools to discover `DEVLOG_CHAT_ID` from an incoming bot
message and send compact development notifications. The helpers load `.env`
without logging values and redact Telegram HTTP/API failures.

Validation:

- Ruff: passed;
- mypy: passed for 5 script modules;
- pytest: 2 passed;
- live test notification: delivered successfully.

### Milestone 1 — Domain Model

Implemented PostgreSQL/SQLAlchemy models for users, configurable lotteries,
draws, immutable tickets, balances, the polymorphic CAS ledger, jackpot
accounts, distribution funds, per-lottery reserves and administrator audit.

Architecture and integrity:

- independent per-lottery draw and global ticket counters;
- unique `(lottery_id, public_number)` constraints;
- integer `BIGINT` storage for all CAS values and balance equations in SQL;
- explicit draw state machine with completed draws as a terminal state;
- PostgreSQL triggers preventing completed draw, settled ticket and ledger
  mutation/deletion;
- idempotency keys and operation IDs for ledger groups;
- row versions on mutable accounts for concurrency diagnostics;
- Weekly and Daily represented as separate configurable lottery entities.

Migration:

- `0001_domain_model` creates all tables, indexes, foreign keys, checks and
  immutability triggers;
- offline PostgreSQL SQL generation passed.

Tests:

- Ruff and formatting passed;
- strict mypy passed for 21 source files;
- pytest: 11 passed.

Resolved:

- reserves are scoped per lottery, following the Milestone 1 requirement.

Known:

- schema migration was compiled offline because local Docker/PostgreSQL is not
  installed; it was not executed against the configured VPS.
- pytest-asyncio emits Python 3.14 deprecation warnings in the current toolchain.

## [0.1.0] - 2026-08-14

### Milestone 0 — Foundation

Established the project foundation as a modular monolith with replaceable bot,
Mini App and Admin clients.

Added:

- repository structure and long-lived agent rules;
- FastAPI application and database-aware health endpoint;
- typed environment configuration with secret placeholders;
- asynchronous SQLAlchemy session infrastructure;
- Alembic migration framework;
- pytest, Ruff and mypy configuration with foundation tests;
- PostgreSQL/API Docker Compose skeleton;
- architecture and open-decisions documentation.

Architecture decisions:

- one backend and one database preserve simple, explicit transaction boundaries;
- domain/application layers remain independent from Telegram and React;
- UTC persistence and explicit Europe/Moscow schedule rules;
- integer CAS and an immutable ledger for every future balance movement.

Risks found:

- reserve scope, integer split remainders and insufficient-reserve behavior need
  owner decisions;
- Daily second draw time, payout model, prices and cart TTL remain unresolved;
- notification delivery must later use an after-commit retry/outbox boundary.

Validation:

- Ruff lint: passed;
- Ruff format check: passed (31 Python files);
- mypy strict check: passed (16 source files);
- pytest: 4 passed;
- Alembic offline SQL generation: passed;
- Docker Compose runtime validation: not run because Docker is not installed in
  the current environment.

Known limitations:

- no domain tables or gameplay logic are included before Milestone 1;
- frontend and bot directories are architectural boundaries only;
- production deployment was intentionally not attempted.
