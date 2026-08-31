# Development log

## [0.14.0] - 2026-08-31

### Final Telegram player release

Сделано:

- implemented three independent Daily entities and migration
  `0010_independent_daily` without reassigning tickets or completed draws;
- added restart-safe post-settlement transfer of legacy Daily funds into PLL
  with paired immutable ledger records;
- set PSS and KHAN base/current jackpots to 24,000,000 CAS;
- upgraded the one-time welcome target to 100,000,000,000 CAS, crediting only
  the difference for identities that received the earlier grant;
- completed the Telegram Mini App for all lottery codes with a mixed cart and a
  premium blue/red/gold responsive theme;
- removed the ordinary player Web frontend, API, login tooling and Admin
  credential controls while retaining historical schema records;
- added exact-lottery buttons to idempotent result/empty-draw notifications;
- retained Telegram favourites, pagination, next-draw screens and large random
  ticket batches from the final gameplay refinement.

Теперь система работает так:

- Telegram bot and Mini App share the same player, balance, tickets and funds;
- PSS/KHAN run immediately; the purchased shared Daily draw settles normally at
  02:22 MSK and then PLL activates automatically with preserved balances;
- Admin remains a permanent independent HTTPS site.

Технически:

- migration: `0010_independent_daily` (head);
- tests: 134 backend + 8 Mini App + 5 Admin passed;
- checks: Ruff, mypy, frontend typecheck/lint/build passed;
- commit: recorded by the release commit.

## [0.13.1] - 2026-08-15

### Web purchase transaction fix

Fixed the Web-only purchase failure reported after production login and made
current jackpots continuously visible.

Done:

- traced the 500 response to an already-open SQLAlchemy transaction created by
  the authentication dependency;
- assigned Weekly and Daily purchase services a fresh uncached database session;
- preserved the service-owned atomic transaction, row locks, ledger and
  idempotency boundaries;
- added a regression test that verifies both purchase routes cannot reuse the
  authentication session;
- added persistent current-jackpot cards for Weekly and Daily;
- refresh balance/jackpots every 15 seconds, on browser focus and manually;
- translated balance, closed-sales and missing-configuration purchase errors.

System behavior:

- a Telegram-authenticated Web player can buy without a nested-transaction 500;
- the exact application service still performs the entire financial operation;
- a failed purchase does not create a ticket or CAS ledger movement;
- current jackpot values remain visible outside an individual lottery tab and
  update without reloading the whole page.

Technical:

- version: 0.13.1;
- migration: no schema change after `0005_telegram_web_login`;
- backend: 46 typed source files, 131 pytest tests;
- frontend: 8 frozen Mini App + 4 Admin + 5 player Web Vitest tests;
- production deployment requires a new explicit owner command.

## [0.13.0] - 2026-08-15

### One-click Telegram Web login

Removed the unnecessary owner/player credential setup from the normal Web
entry path while preserving password login as a fallback.

Done:

- added **🌐 Открыть Web-версию** to the Telegram main menu;
- added `/web` as a direct command;
- issue a separate one-time link for the currently bound Telegram identity;
- exchange the link for the existing signed HttpOnly Web session;
- allow Web sessions to use the stable player identity without a password row;
- consume tokens transactionally under a database row lock;
- remove the raw token from browser history before the API exchange;
- added expired/reused token handling and a clear retry message;
- retained Admin-created Argon2 Web credentials as an optional fallback;
- updated production configuration and owner/player documentation.

System behavior:

- each Telegram account enters Web under its own K-Loto user in two button taps;
- opening a link from another Telegram account switches the browser session;
- no Web username or password is required for the normal flow;
- a link works once and expires after five minutes;
- balance, active tickets and history are the same in bot and Web.

Technical:

- version: 0.13.0;
- migration: `0005_telegram_web_login`;
- backend: 46 typed source files, 130 pytest tests;
- frontend: 8 frozen Mini App + 4 Admin + 5 player Web Vitest tests;
- Ruff, formatting, mypy and all frontend typecheck/lint/build checks passed;
- Alembic single-head and offline upgrade SQL checks passed;
- production backup completed before migration;
- live migration head: `0005_telegram_web_login`;
- live `alembic check`: no new upgrade operations detected;
- production exchange verified: first login 200, session restore 200, reuse 401;
- Telegram command registration verified: `/start`, `/menu`, `/web`;
- API, bot and gateway restart counts after verification: zero.

## [0.12.0] - 2026-08-15

### Production deployment

Deployed the complete K-Loto backend, scheduler, Telegram bot, player Web and
Admin Panel to the owner-authorized VPS without changing existing VPN services.

Done:

- added a production Docker Compose stack with private PostgreSQL storage;
- built static player Web and Admin clients behind a Caddy HTTPS gateway;
- configured free `sslip.io` hostnames and automatic TLS on port 9443;
- enabled API startup recovery and continuous draw scheduling;
- enabled one persistent Telegram polling bot and notification outbox worker;
- added idempotent Weekly/Daily bootstrap with one future draw per lottery;
- added a compressed database backup script, private backup volume and daily
  cron execution with 14-day retention;
- stored runtime credentials only in ignored/restricted environment files;
- added Admin-based Web credential provisioning for a Telegram-bound player;
- fixed asyncpg compatibility in the initial trigger migrations;
- aligned historical check-constraint names with current metadata.

System behavior:

- backend, scheduler, bot, player Web and Admin restart automatically after a
  process or VPS restart;
- Weekly and both Daily slots are available from the same persistent database;
- the owner can credit a player, configure prices/base jackpots/reserves and
  create a browser login from Admin;
- the player can buy from Telegram or the ordinary browser site;
- HTTPS, database storage and backups no longer depend on the owner's computer;
- the existing VPN continues using its original ports unchanged.

Technical:

- version: 0.12.0;
- migration: `0004_constraint_names` (single live head);
- backend: 45 typed source files, 126 pytest tests;
- frontend: 8 frozen Mini App + 4 Admin + 4 player Web Vitest tests;
- Ruff, formatting, mypy, frontend typecheck/lint/build and secret scan passed;
- live `alembic check`: no new upgrade operations detected;
- live HTTPS/Web/Admin/API/bot/database checks passed;
- API, bot and gateway restart counts after verification: zero;
- an initial non-empty database backup was successfully created.

## [0.11.0] - 2026-08-15

### Daily Lottery 4/15

Implemented the owner-approved Daily economics, scheduling, recovery and player
interfaces without changing Weekly rules or the frozen Mini App frontend.

Done:

- implemented strict Daily 4-of-15 ticket validation and secure RNG support;
- split every purchase into 40% jackpot and 60% distribution ledger credits;
- implemented 0/4 and 1/4 zero payout, 2/4 half-price payout, 3/4 triple-price
  payout and per-ticket sharing of the full jackpot at 4/4;
- used distribution then per-lottery reserve for guaranteed payout shortfall;
- preserved unused distribution and unwon jackpot carryovers;
- reset a won jackpot to the Admin-configured base amount through ledger;
- enabled both 02:22 and 18:00 MSK slots with a two-minute cutoff;
- generalized chronological recovery to Weekly and Daily draws;
- enabled Daily multi-ticket checkout in Telegram and ordinary Web;
- added Daily rules to bot help and all relevant documentation;
- added audited Admin provisioning of player Web credentials;
- recorded OD-006 and OD-012 as resolved.

System behavior:

- Weekly and Daily retain independent draw/ticket numbering and fund accounts;
- identical Daily combinations are separate tickets;
- empty Daily draws complete and carry both pools;
- repeated purchase or settlement invocation cannot debit or pay twice;
- insufficient reserve leaves the whole draw unsettled for safe later retry;
- price, base jackpot and reserve stay owner-controlled in Admin.

Technical:

- version: 0.11.0;
- migration: no schema change after `0003_web_accounts`;
- backend: 45 typed source files, 124 pytest tests;
- frontend: 8 frozen Mini App + 4 Admin + 4 player Web Vitest tests;
- Ruff, formatting, mypy and all frontend typecheck/lint/build checks passed;
- no VPS deployment was included in this release commit.

## [0.10.0] - 2026-08-15

### Player Web

Delivered the simple ordinary-browser player interface requested before Daily,
without changing the frozen Telegram Mini App or duplicating domain logic.

Done:

- added one-to-one `web_accounts` credentials linked to existing regular users;
- added Argon2 password hashing and normalized unique usernames;
- added signed expiring HttpOnly player sessions with CSRF validation;
- added authenticated dashboard, ticket, draw-result and Weekly purchase routes;
- reused `MiniAppQueryService` projections and
  `WeeklyTicketPurchaseService` transaction/ledger guarantees;
- added a minimal responsive React client for balance and Weekly 5 of 20;
- added manual number selection and purchase quantity from 1 to 20;
- added active tickets, settled history and global completed-draw results;
- added a secret-safe interactive Web account configurator and local start script;
- updated architecture, deployment and operator documentation;
- expanded standard checks to all three frontend clients.

System behavior:

- Telegram and Web logins reach the same player, integer CAS balance, tickets
  and immutable results;
- repeated purchase transport delivery remains idempotent and cannot debit the
  balance twice;
- identical combinations remain allowed as separate tickets;
- inactive accounts/users are rejected, and a browser cannot edit balances,
  prices, draws or settlement data;
- production cookies become Secure automatically; local Vite uses a same-origin
  API proxy and does not enable the frozen Mini App development bypass.

Technical:

- version: 0.10.0;
- migration: `0003_web_accounts` (single Alembic head; offline upgrade SQL passed);
- backend: 43 typed source files, 101 pytest tests;
- frontend: 8 frozen Mini App + 4 Admin + 3 player Web Vitest tests;
- all three frontend typecheck, lint and production builds passed;
- implementation secret scan passed; `.env` remains ignored;
- live `alembic check` remains unavailable locally because this machine has no
  PostgreSQL service; migration-chain and offline DDL checks passed;
- no VPS connection or deployment was attempted in this release.

Known:

- Daily payouts and cutoff remain owner decisions OD-006 and OD-012;
- final deployment waits for those rules and the Daily implementation.

## [0.9.0] - 2026-08-15

### Telegram Bot Gameplay

Promoted the aiogram bot from notification adapter to the primary complete
player interface while keeping all business rules in application/domain layers.

Done:

- `/start` now binds identity and opens the live K-Loto gameplay dashboard;
- added balance, Weekly/Daily cards, jackpot, next draw and active-ticket count;
- added Weekly 5/20 inline picker with strict five-number selection;
- added `SystemRandom` random pick, clear, cart and atomic checkout controls;
- identical combinations are preserved as separate tickets;
- the configurable bot cart supports 20 tickets by default;
- each transient cart gets one stable checkout identity for safe callback retries;
- checkout calls the existing locked `WeeklyTicketPurchaseService` and durable
  purchase notification outbox;
- added active tickets, settled history, global results, rules and player
  spend/win/net/match statistics;
- Daily remains visible but blocked until OD-006 and OD-012 are resolved;
- added `/menu` and registered Telegram command descriptions;
- preserved the frozen Mini App compatibility code without using it in the menu;
- documented the final always-on HTTPS Admin/API/bot/Web deployment topology.

System behavior:

- a player can select numbers and buy one or many Weekly tickets entirely in
  Telegram without a domain or Mini App;
- backend remains the source of truth for balance, price, draw and settlement;
- repeated Telegram checkout delivery returns the existing purchase instead of
  charging twice;
- unpaid cart state may be lost on bot restart, but no ticket or CAS exists until
  atomic checkout commits;
- purchased tickets, ledger history, results and notifications remain durable;
- Admin will later be an ordinary persistent website, not an owner-run local
  development process.

Technical:

- version: 0.9.0;
- migration: no schema change after `0002_notification_outbox`;
- backend: 41 typed source files, 95 pytest tests;
- frontend regression: 8 frozen Mini App + 4 Admin Vitest tests;
- Telegram transport batch limit: `BOT_MAX_TICKETS_PER_PURCHASE` (default 20);
- no production/VPS connection or deployment was attempted.

Known:

- the unpaid Telegram picker/cart uses in-memory FSM state for the planned
  single bot replica; shared state is needed only if bot replicas are added;
- Daily purchase remains intentionally unavailable;
- next stage is the simple player Web client, followed by one owner-authorized
  permanent deployment of backend, bot, Web and Admin.

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
