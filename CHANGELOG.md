# Changelog

All notable changes follow Keep a Changelog and Semantic Versioning principles.

## [0.14.0] - 2026-08-31

### Added

- Independent ПЛЛ-лото, ПСС-Лото and ХАН-Лото with separate draws, ticket
  numbering and funds at 02:22, 12:00 and 18:00 Moscow time.
- One-time automatic 100,000,000,000 CAS Telegram welcome allocation.
- Premium blue/red/gold Telegram Mini App for all four lotteries.
- Empty-draw broadcasts with current jackpot and a direct purchase button.
- Telegram favourites, next-draw countdowns, ticket pagination and random
  batches of 5, 10, 25 or 50 tickets.

### Changed

- ПСС and ХАН start with independent 24,000,000 CAS jackpots; ПЛЛ safely
  inherits the shared Daily funds after already purchased tickets settle.
- The Telegram bot and Mini App are now the only player interfaces.
- Web Admin remains a separate permanent HTTPS site and is fully localized.

### Removed

- Ordinary username/password player Web application and its runtime API.

### Fixed

- Daily selection now remains bound to the exact chosen lottery and draw.
- Admin saves lottery price, base jackpot and reserve with clear feedback.

## [0.13.1] - 2026-08-15

### Changed

- Weekly and Daily current jackpots are always visible in the player Web header.
- Jackpot and balance information refresh automatically every 15 seconds, when
  the browser regains focus and by an explicit refresh button.
- Web purchase failures now return clear Russian explanations.

### Fixed

- Fixed Web purchases failing after authentication because the authentication
  query and protected financial operation shared one SQLAlchemy transaction.

## [0.13.0] - 2026-08-15

### Added

- One-click player Web login directly from each Telegram account.
- `/web` bot command and a permanent Web button in the main bot menu.
- Five-minute one-time login tokens with migration
  `0005_telegram_web_login`.

### Changed

- Manual Web username/password provisioning is now an optional fallback instead
  of a required setup step.
- The player Web login page now points users to the simpler Telegram flow.

### Security

- Only SHA-256 token hashes are stored in PostgreSQL.
- Raw one-time tokens use URL fragments, do not enter server request URLs and
  are atomically invalidated after the first successful exchange.

## [0.12.0] - 2026-08-15

### Added

- Permanent HTTPS player Web and Admin sites on the owner-authorized VPS.
- Always-on API, scheduler, recovery worker, Telegram bot and PostgreSQL stack.
- Idempotent production bootstrap for Weekly/Daily lotteries and their next draws.
- Daily compressed PostgreSQL backups with 14-day retention.
- Production operation and first-player setup documentation.

### Changed

- Database check-constraint names now match SQLAlchemy metadata through migration
  `0004_constraint_names`.
- PostgreSQL trigger creation in the initial migrations is compatible with the
  asyncpg prepared-statement execution model.

### Security

- PostgreSQL remains private to the Docker network; HTTPS certificates renew
  automatically through Caddy.
- Production credentials exist only in the ignored owner `.env` and the
  permission-restricted VPS environment file.
- Existing VPS VPN services and their ports remain untouched.

## [0.11.0] - 2026-08-15

### Added

- Fully playable Daily Lottery 4 of 15 in Telegram and player Web.
- Daily draws at 02:22 and 18:00 Europe/Moscow with a two-minute cutoff.
- Daily 40/60 jackpot/distribution contributions and approved prize tiers.
- Daily settlement, reserve fallback, carryovers, jackpot reset and recovery.
- Audited Web-login provisioning for players from the Admin Panel.

### Changed

- Scheduler recovery now settles overdue Weekly and Daily draws in one
  chronological sequence.
- Player Web and Admin clients are versioned with the Daily release.

### Security

- Daily purchases and settlement use row locks, immutable ledger records,
  idempotency keys and durable notification events.
- Guaranteed Daily prizes never consume jackpot; insufficient reserve aborts
  settlement atomically.

## [0.10.0] - 2026-08-15

### Added

- Ordinary browser player application with Weekly 5/20 gameplay.
- Password login, current CAS balance, active tickets and settled history.
- Completed draw result archive and 1-to-20-ticket purchase interface.
- One-to-one Web accounts for existing players and migration
  `0003_web_accounts`.
- Local account configurator and player Web start command.

### Changed

- Standard project checks now validate and build the frozen Mini App, Admin
  Panel and ordinary player Web client.
- The permanent deployment plan now has a defined player Web authentication
  flow.

### Security

- Player passwords use Argon2 hashes and are never returned to the browser.
- Signed expiring HttpOnly sessions use an independent secret, SameSite/Secure
  cookie controls and per-session CSRF protection.
- Weekly purchases remain server-authoritative, atomic and idempotent through
  the existing application service and immutable ledger.

## [0.9.0] - 2026-08-15

### Added

- Complete Telegram bot gameplay menu with balance, lotteries and rules.
- Weekly 5/20 inline number picker, secure random pick and multi-ticket cart.
- Atomic Telegram checkout with duplicate-combination support and idempotency.
- Active tickets, settled history, recent draw archive and player statistics.
- Configurable Telegram purchase batch limit.
- Permanent deployment plan for always-on API, bot, user Web and Admin site.

### Changed

- Telegram bot is now the primary player interface; the Mini App remains frozen.
- Admin production target is an ordinary continuously available HTTPS website,
  while local start commands remain development-only.

### Security

- Telegram prices, draw assignment, balances and payouts remain server-authoritative.
- Repeated checkout callbacks use one stable idempotency identity and cannot
  create a second financial operation.

## [0.8.0] - 2026-08-15

### Added

- Separate authenticated Web Admin Panel with operational dashboard.
- Player financial overview and idempotent balance adjustments through ledger.
- Lottery price/base-jackpot configuration and reserve ledger adjustments.
- Filterable immutable CAS ledger, administrator audit and read-only draw archive.
- Number appearance statistics derived from completed draw history.
- Argon2 administrator credential setup, signed HttpOnly sessions and CSRF protection.

### Changed

- Telegram Mini App is preserved but frozen; active player UI roadmap is now the
  full Telegram bot followed by a simple user Web version.
- Standard frontend checks now cover both the preserved Mini App and Admin Panel.

### Security

- Administrator mutations require an authenticated session, CSRF token,
  mandatory reason and backend ledger/audit use cases.
- Completed draws have no administrator mutation endpoint.

## [0.7.0] - 2026-08-15

### Added

- One-command local browser development mode without Telegram authentication.
- Idempotent local test player, playable lottery fixtures and ledgered test CAS.
- Development-only balance refill through the immutable ledger.
- Loopback-only signed HttpOnly development sessions.
- Separate Telegram tunnel frontend mode with a free Cloudflare Quick Tunnel
  helper and no browser authentication bypass.
- Beginner-focused local PostgreSQL, browser and Telegram tunnel guide.

## [0.6.0] - 2026-08-15

### Added

- Telegram Mini App dashboard with balance, Weekly/Daily cards, jackpots and
  countdowns.
- Weekly 5/20 number picker, random selection and single-ticket purchase.
- Multi-ticket cart checkout with configurable expiring persistence.
- Active tickets, completed history and recent results.
- Server-side Telegram `initData` authentication for every Mini App request.
- Configurable Mini App launch button in the Telegram bot.

### Fixed

- Purchases after the Weekly cutoff now atomically prepare and use the next
  numbered draw without waiting for the current draw settlement.

## [0.5.0] - 2026-08-14

### Added

- Telegram player bot with `/start` and idempotent user/balance binding.
- Purchase confirmations for single and multi-ticket orders.
- Per-user Weekly draw-result notifications, including losing tickets.
- Durable notification outbox with retry, recovery and duplicate protection.
- Separate bot runtime for local and Docker Compose operation.

## [0.4.0] - 2026-08-14

### Added

- Weekly schedule at Sunday 20:00 Europe/Moscow with a 19:55 sales cutoff.
- Automatic preparation and independent numbering of the next draw.
- Startup and periodic reconciliation of missed Weekly draws.
- Chronological recovery of several missed draws after downtime.
- Confirmed Daily schedule slots at 02:22 and 18:00 Europe/Moscow.
- APScheduler runtime integrated with backend application lifespan.

## [0.3.0] - 2026-08-14

### Added

- Atomic single- and multi-ticket purchases for Weekly 5/20.
- Server-authoritative draw selection after a sales cutoff.
- Complete Weekly payout calculation for categories 0/5 through 5/5.
- Jackpot and distribution contributions, carryovers and jackpot reset.
- Reserve fallback for guaranteed 2/5 and 3/5 prizes.
- Cryptographically secure official draw generation.
- Idempotent purchase and settlement processing, including empty draws.

## [0.2.0] - 2026-08-14

### Added

- Secret-safe Telegram DevLog chat discovery and notification scripts.
- Complete initial domain schema for users, lotteries, draws, tickets, CAS
  accounts, immutable ledger and administrator audit history.
- Database-enforced immutable completed draws, settled tickets and ledger rows.
- Independent per-lottery draw and ticket numbering foundations.

## [0.1.0] - 2026-08-14

### Added

- Initial K-Loto project foundation.
- FastAPI service with application/database health reporting.
- PostgreSQL, SQLAlchemy and Alembic configuration skeleton.
- Docker Compose development stack.
- Test, lint, format and type-check configuration.
- Architecture, security and unresolved-decision documentation.
