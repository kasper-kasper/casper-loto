# Development log

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
