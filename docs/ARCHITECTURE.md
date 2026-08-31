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

The scheduler calculates official times in `Europe/Moscow`, stores UTC, settles
missed draws chronologically and relies on row locks and constraints for
idempotency. Each active lottery maintains its own next draw. Completed draws
are protected by a database trigger.

The v0.14.0 transition preserves the final shared Daily draw and its purchased
tickets. PSS and KHAN start independently at deployment. After the legacy draw
settles, an idempotent recovery service ledger-transfers its jackpot,
distribution and reserve into PLL and activates PLL. No ticket or completed draw
is reassigned.
