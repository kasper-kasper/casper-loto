# Scheduler and recovery

K-Loto calculates every official schedule in `Europe/Moscow` and persists
timezone-aware UTC timestamps.

## Slots

- Weekly: Sunday 20:00 MSK; sales close Sunday 19:55 MSK.
- Daily: 02:22 and 18:00 MSK. Daily sales cutoff and payout rules remain open,
  so Daily settlement and sales are not enabled yet.

The first launch prepares only the nearest future draw. It never fabricates
historical draws from before the system existed.

## Recovery

Backend lifespan performs reconciliation before starting the periodic
APScheduler job. For every active lottery it ensures one pending draw exists.
Overdue Weekly draws are then processed globally in ascending `scheduled_at`
order. After each settlement, the next draw is created from the previous
official scheduled time; this naturally reconstructs several missed draws.

The system remains safe if more than one scheduler starts:

- a lock on the lottery row serializes draw-number allocation;
- `(lottery_id, public_number)` is unique;
- settlement locks the draw and all CAS accounts;
- completed status and unique ledger idempotency keys prevent repeat payouts;
- the same reconciliation operation is safe after process restart.

`scheduled_at` never changes during recovery. `executed_at` records when the
server actually completed the delayed draw.
