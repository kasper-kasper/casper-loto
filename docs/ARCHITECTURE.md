# Architecture

K-Loto uses a layered backend. Domain calculations are pure; application
services own transactions and idempotency; FastAPI, Telegram, scheduler and Web
Admin are adapters. PostgreSQL is authoritative. CAS is always an integer and
every balance/fund movement has an immutable ledger record.

The Telegram bot is the notification and entry adapter; all active gameplay is
in the Telegram Mini App. The Mini App authenticates signed Telegram `initData`
on every request. A loopback-only
development cookie exists only when `APP_ENV=development` and the explicit dev
switch is enabled. The ordinary username/password player Web adapter is retired.

The Admin Panel is a separate HTTPS application with signed sessions, CSRF
protection and audited mutations. Administrators cannot mutate completed draws
or purchased tickets. Versioned CHANGELOG and DEVLOG history is exposed there
through authenticated, read-only endpoints. Telegram journal delivery is
retired; Telegram remains a player entry and notification adapter.

The Mini App live-draw adapter is deliberately read-only. A server-authored
timeline defines broadcast start, every number reveal and completion. An
authenticated SSE stream pushes compact snapshots; reconnecting clients derive
the correct stage from server time and never restart the draw locally. RNG,
settlement, recovery and draw state remain in the existing domain/application
services. At most three representative player tickets are returned, so a player
with thousands of tickets does not create an unbounded live response.

Player sales state is treated as volatile. The Mini App dashboard carries a
server timestamp and per-draw player ticket counts, refreshes periodically and
on visibility restoration, and performs one fresh read immediately before the
number picker opens. Cached or stale UI state can therefore never be the final
authority for displaying a closed-sale message; the transactional purchase
service still makes the authoritative cutoff decision.

High-volume Mini App checkout is bounded at both layers: 1,000 client-side cart
entries and 1,000 combinations per application-service purchase, with a default
5,000-ticket per-player/per-draw cap and request throttling. Each lottery group
is processed by one idempotent database transaction instead of client-side
batches. An optional five-draw choice creates tickets for the current and next
four draws and debits the complete cost once, without automatic renewal.

Player communication is split into two durable projections. Telegram delivery
uses the existing outbox only after explicit per-user consent and is limited to
the player's own draw results and 24-hour inactivity reminders. The Mini App
inbox stores wins and draw invitations independently; its event body is
immutable and only `read_at` may change.

Auto-play is an application service invoked after scheduler recovery. It scans
explicit per-user settings, generates five combinations with `SystemRandom`,
and delegates to the same transactional purchase service as manual checkout.
A stable user/draw idempotency key plus the persisted `AUTO_PLAY` ticket source
prevents duplicate sets after retries or server restarts.

The scheduler calculates official times in `Europe/Moscow`, stores UTC, settles
missed draws chronologically and relies on row locks and constraints for
idempotency. Each active lottery maintains its own next draw. Completed draws
are protected by a database trigger.

Lottery mathematics is selected by `lotteries.ruleset_code`. Declarative rule
strategies contain the format, integer price split, proportional or fixed
payouts, jackpot tier and central Kasper-Fund-funded
jackpot refill. Purchase and settlement are code-agnostic. Schedule
dispatch separately supports weekly, slot-based and interval strategies. See
`docs/LOTTERY_STRATEGIES.md`.

The v0.14.0 transition preserves the final shared Daily draw and its purchased
tickets. PSS and KHAN start independently at deployment. After the legacy draw
settles, an idempotent recovery service ledger-transfers its jackpot,
distribution and reserve into PLL and activates PLL. No ticket or completed draw
is reassigned.
