# Telegram bot and notification delivery

The player bot is an aiogram 3.x adapter. It contains no lottery mathematics or
CAS mutation logic.

## User binding

`/start` upserts a user by positive Telegram ID and creates the user's zero-CAS
balance if missing. Repeated `/start` updates the display identity without
creating another user or balance. The response explains that ticket purchases
will be available only through the Mini App; the bot exposes no purchase
buttons.

## Durable notifications

Ticket checkout inserts one purchase event for the whole multi-ticket order in
the same transaction as the tickets and ledger. Weekly settlement inserts one
result event per participating user, including losing results. If the business
transaction rolls back, its notification rolls back too.

The worker claims one available event using `FOR UPDATE SKIP LOCKED`, marks it
as processing, sends it and then marks it sent. Unique event keys prevent a
second event for an idempotent purchase or settlement. Failed sends use
exponential backoff, stale processing locks are recoverable, and only redacted
error codes are stored.

PostgreSQL protects event identity and payload from updates or deletion and
makes sent events terminal. Telegram itself does not support an idempotency key,
so a crash in the narrow interval after Telegram accepts the message and before
`SENT` is committed can cause a repeated message. It cannot duplicate a ticket,
payout or draw settlement.
