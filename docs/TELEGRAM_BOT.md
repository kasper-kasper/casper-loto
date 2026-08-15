# Telegram gameplay bot

The aiogram 3.x bot is the primary player interface and contains no lottery
mathematics or direct CAS mutations.

## Player interface

`/start` upserts a user by positive Telegram ID and creates the user's zero-CAS
balance if missing. Repeated `/start` updates the display identity without
creating another user or balance. It opens a server-authoritative gameplay menu:

- balance and current Weekly/Daily cards;
- Weekly 5/20 and Daily 4/15 pickers with cryptographically secure random pick;
- a multi-ticket cart with identical combinations allowed;
- atomic checkout through the matching Weekly or Daily purchase service;
- active tickets and settled ticket history;
- recent immutable draw results;
- player spend/win/net and match statistics;
- approved Weekly and Daily rules.

The Telegram cart is transient conversation state and creates no ticket or CAS
movement before checkout. A configured transport limit
`BOT_MAX_TICKETS_PER_PURCHASE` defaults to 20 and can be changed without changing
lottery economics. Every cart receives a stable checkout identity, so repeated
callback delivery reaches the existing idempotent purchase use case.

Daily is purchasable when its Admin-configured price and funds are ready. It
uses 40/60 fund contributions, fixed 2/4 and 3/4 payouts, jackpot 4/4 and a
two-minute cutoff. The preserved Mini App is not launched from the new main menu
and remains frozen without deleting its code.

## Commands

- `/start` — bind identity and open K-Loto;
- `/menu` — discard transient picker state and return to the main menu.

## Durable notifications

Ticket checkout inserts one purchase event for the whole multi-ticket order in
the same transaction as the tickets and ledger. Draw settlement inserts one
result event per participating user, including losing results. If the business
transaction rolls back, its notification rolls back too.

The worker claims one available event using `FOR UPDATE SKIP LOCKED`, marks it
as processing, sends it and then marks it sent. Unique event keys prevent a
second event for an idempotent purchase or settlement. Failed sends use
exponential backoff, stale processing locks are recoverable, and only redacted
error codes are stored.

PostgreSQL protects event identity and payload from updates or deletion and
makes sent events terminal. Telegram itself does not support an idempotency key,
so a crash in the narrow interval after Telegram accepts a message and before
`SENT` is committed can cause a repeated message. It cannot duplicate a ticket,
payout or draw settlement.

## Process model

The personal deployment runs one bot polling process with automatic restart.
The in-progress picker/cart uses aiogram memory storage; a bot restart may clear
an unpaid cart, but purchased tickets and CAS history are unaffected. A future
multi-replica bot would replace this adapter state with shared storage without
changing domain services.
