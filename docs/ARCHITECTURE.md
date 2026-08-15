# Architecture

## Decision

K-Loto starts as a modular monolith with one PostgreSQL database. This keeps
cross-account CAS transfers, ticket purchases and draw settlement within clear
database transaction boundaries while avoiding premature distributed-system
complexity. The bot and both web interfaces remain replaceable adapters.

Dependency direction is inward:

```text
API / bot / scheduler -> application -> domain
                              |
                              v
                    infrastructure ports
```

The domain layer owns lottery invariants and calculations. Application services
orchestrate transactions and authorization. Infrastructure implements database,
Telegram, clock, random-number and notification adapters. Transport layers map
requests and responses only.

The Telegram Mini App adapter is frozen after v0.7.0 and retained without
removal. The active product clients are now the Telegram bot, the ordinary user
Web client and the separate Web Admin Panel. All share the same application
services; no business rule is moved into a client during this transition.

The preserved Mini App sends Telegram `initData` on every request. The backend validates
its HMAC signature and age before binding the Telegram identity. Client values
for balance, ticket price and draw assignment are display-only and never trusted.

Local browser authentication is a separate development-only adapter. It needs
an explicit flag and secret, accepts only loopback client/Host/Origin, and uses
a short-lived HttpOnly SameSite cookie. `APP_ENV=production` disables it even if
other flags are accidentally present. Public tunnels run a separate frontend
mode and the tunnel helper refuses to start while the bypass flag is enabled.

The Admin Panel uses an independent Argon2 credential, a signed short-lived
HttpOnly SameSite session and a per-session CSRF token. Administrator mutations
call backend use cases that lock accounts and write ledger plus audit records in
one transaction. Draw endpoints are read-only, including for administrators.

The player Web client uses one Argon2 credential row per existing regular user.
Its signed HttpOnly session contains stable account/user identifiers and a CSRF
token. It calls the same query and Weekly purchase application services as the
other adapters, so balances, tickets and results are shared with Telegram.

Telegram bot gameplay is a stateful transport adapter over the existing query
and Weekly purchase services. Only the unpaid picker/cart lives in aiogram
memory; tickets, checkout idempotency, CAS and notifications remain durable in
PostgreSQL. One polling replica is planned for the first permanent deployment.

The deployment target serves Admin and the player Web build as ordinary
HTTPS sites through a reverse proxy. Static assets, API, bot and scheduler start
automatically with the server; an owner opens the Admin URL and signs in without
running local commands. Local Vite/PowerShell workflows remain development-only.

## Planned backend modules

- `identity`: users and external identities without Telegram coupling.
- `lotteries`: configurable lottery definitions and schedules.
- `draws`: lifecycle, secure RNG, recovery and immutable results.
- `tickets`: validation, cart checkout and immutable purchased tickets.
- `finance`: balances, ledger, jackpots, distribution funds and reserves.
- `audit`: administrator actions and correction records.
- `notifications`: durable outbox-driven player notifications.

Modules may share one database but must interact through application services,
not by embedding business rules in controllers or UI code.

## Time and scheduling

Database timestamps are timezone-aware UTC values. Schedule generation uses an
explicit `ZoneInfo("Europe/Moscow")` clock. A draw stores at least `scheduled_at`
and `executed_at`. Startup reconciliation discovers overdue, non-completed draws
and processes them in chronological order. Empty draws still complete.

## Transaction boundaries

The following operations must be atomic and concurrency-safe:

- multi-ticket checkout, balance debit and fund contributions;
- allocation of per-lottery public draw and ticket numbers;
- draw lock, result creation, settlement, payouts and carryovers;
- administrative balance/reserve adjustments plus audit and ledger entries.

Uniqueness constraints and row locks are required in addition to application
checks. Notification events are inserted inside the purchase/settlement
transaction. Telegram delivery occurs after commit through an outbox, so
transport failure cannot roll back a completed business transaction.

## Architectural risks and contradictions

No game rule is changed here; these are implementation hazards to resolve in
later milestones:

1. **Admin “set balance” is not direct mutation.** It must become a delta ledger
   transaction plus audit record under one database transaction.
2. **Draw recovery and schedule changes interact.** Editing schedules must never
   rewrite already prepared or completed official draws; effective-date rules
   should be defined before schedule editing is built.
3. **Telegram has no caller-supplied idempotency key.** Unique outbox event keys,
   row locks and terminal sent records prevent normal duplicate dispatch. A
   process crash after Telegram accepts a message but before the database marks
   it sent may still produce a repeated delivery; business settlement remains
   exactly-once and unaffected.

Per-lottery reserves, deterministic whole-CAS remainder allocation and atomic
retry on insufficient reserve are now resolved. Daily slots are 02:22 and 18:00
Europe/Moscow; its payout model and sales cutoff remain deliberately undefined.
