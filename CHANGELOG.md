# Changelog

All notable changes follow Keep a Changelog and Semantic Versioning principles.

## [Unreleased]

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
