# Daily Core 4/15

Daily is a separately configured lottery entity with independent draw and
ticket numbering. It draws four unique numbers from 1 through 15 at 02:22 and
18:00 Europe/Moscow. Sales close two minutes before each slot.

## Purchase

- ticket price is configured in Admin and must be divisible by 10 CAS;
- 40% of every purchase credits the Daily jackpot;
- 60% credits the Daily distribution fund;
- multi-ticket purchases are atomic and identical combinations are allowed;
- every CAS movement is recorded in the immutable ledger.

## Settlement

- 0/4 and 1/4: 0 CAS;
- 2/4: 50% of that ticket's immutable purchase-price snapshot;
- 3/4: 300% of that ticket's immutable purchase-price snapshot;
- 4/4: the full current jackpot, divided per winning ticket;
- whole-CAS remainders go to ascending public ticket numbers;
- guaranteed 2/4 and 3/4 payouts consume distribution first and then the
  per-lottery reserve; jackpot is never used for that shortfall;
- insufficient reserve aborts settlement atomically for later recovery;
- unused distribution and an unwon jackpot carry forward;
- after any 4/4 win the jackpot resets to the Admin-configured base jackpot;
- empty draws complete and preserve both funds.

Settlement uses `secrets.SystemRandom`, row locks, terminal completed state,
unique ledger/outbox keys and a single database transaction. Scheduler recovery
processes overdue Weekly and Daily draws globally in chronological order.
