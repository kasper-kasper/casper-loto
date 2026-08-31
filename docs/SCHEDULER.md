# Scheduler and recovery

K-Loto calculates every official schedule in `Europe/Moscow` and persists
timezone-aware UTC timestamps.

## Slots

- Weekly: Sunday 20:00 MSK; sales close Sunday 19:55 MSK.
- Unified Daily: ПЛЛ-лото at 02:22 (cutoff 02:20), ПСС-лото at 12:00
  (cutoff 11:58) and ХАН-лото at 18:00 (cutoff 17:58) MSK. All slots use the
  same lottery funds and sequential draw numbering.

The first launch prepares only the nearest future draw. It never fabricates
historical draws from before the system existed.

## Recovery

Backend lifespan performs reconciliation before starting the periodic
APScheduler job. For every active lottery it ensures one pending draw exists.
Overdue Weekly and Daily draws are processed globally in ascending `scheduled_at`
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
