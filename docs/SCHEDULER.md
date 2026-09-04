# Scheduler and recovery

K-Loto calculates every official schedule in `Europe/Moscow` and stores aware
UTC timestamps. The authoritative human-readable table is
[`LOTTERY_SCHEDULE.md`](LOTTERY_SCHEDULE.md).

Slot lotteries keep enough future draws for their configured daily schedule.
FLASH, SHADOW and PULSE use the same generic interval strategy with two future draws
prepared per lottery. Their ten-minute alternation is produced by two separate
twenty-minute schedules anchored at `00:00` and `00:10` Moscow.

The first launch prepares only future draws. It never fabricates history from
before a lottery existed. The Mini App dashboard selects the first scheduled
draw whose cutoff is still in the future, so a just-closed draw cannot hide the
next purchasable one.

## Recovery

Backend lifespan performs reconciliation before starting the periodic
APScheduler job. For every active lottery it ensures the configured number of
pending draws exists. Overdue draws are processed globally in ascending
`scheduled_at` order. After each settlement, the next draw is created from the
previous official scheduled time; this reconstructs missed draws without time
drift.

The system remains safe if more than one scheduler starts:

- a lock on the lottery row serializes draw-number allocation;
- `(lottery_id, public_number)` and `(lottery_id, scheduled_at)` are unique;
- settlement locks the draw and all CAS accounts;
- completed status and unique ledger idempotency keys prevent repeat payouts;
- the same reconciliation operation is safe after process restart.

`scheduled_at` never changes during recovery. `executed_at` records when the
server actually completed a delayed draw.
