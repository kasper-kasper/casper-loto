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

## Planned backend modules

- `identity`: users and external identities without Telegram coupling.
- `lotteries`: configurable lottery definitions and schedules.
- `draws`: lifecycle, secure RNG, recovery and immutable results.
- `tickets`: validation, cart checkout and immutable purchased tickets.
- `finance`: balances, ledger, jackpots, distribution funds and reserves.
- `audit`: administrator actions and correction records.
- `notifications`: outbox-driven player/devlog notifications when implemented.

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
checks. External notifications occur after commit, eventually through an outbox,
so Telegram failure cannot roll back a completed business transaction.

## Architectural risks and contradictions

No game rule is changed here; these are implementation hazards to resolve in
later milestones:

1. **Admin “set balance” is not direct mutation.** It must become a delta ledger
   transaction plus audit record under one database transaction.
2. **Draw recovery and schedule changes interact.** Editing schedules must never
   rewrite already prepared or completed official draws; effective-date rules
   should be defined before schedule editing is built.
3. **Notifications are not part of settlement atomicity.** A durable retry/outbox
   boundary is needed to prevent duplicate messages without risking duplicate
   payouts.

Per-lottery reserves, deterministic whole-CAS remainder allocation and atomic
retry on insufficient reserve are now resolved. Daily slots are 02:22 and 18:00
Europe/Moscow; its payout model and sales cutoff remain deliberately undefined.
