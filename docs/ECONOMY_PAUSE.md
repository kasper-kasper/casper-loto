# Planned economy pause — 18 October 2026

The owner explicitly requested that the Mini App stay closed until a further instruction. There is no scheduled reopening. DEVLOG and CHANGELOG updates are deferred by the owner.

## Recorded cutoff

2026-10-17T22:33:45.277901Z (18 October 2026, 01:33:45 Moscow). The gateway closed and workers stopped before this cutoff was recorded; the due-draw drain found zero unfinished due draws. The deployment operation holds `/run/lock/k-loto-operations.lock`, backs up the database and preserves diagnostic logs.

## Durable state and transition

`economy_control` is a singleton. It stores the pause, cutoff, current epoch and applied batch IDs. `scripts.economy_transition --cutoff <UTC timestamp>` invokes the audited application service; it deliberately has no reopen option. Retrying an applied batch does not refund twice, reset jackpots twice, advance the epoch again or reopen the application.

Every purchase, settlement and draw creation acquires a shared transaction advisory lock and checks the pause. The transition takes the exclusive lock. Due or already started obligations block the transition until resolved. Future tickets become REFUNDED using compensating ledger entries. Dual refunds use Kasper Fund, where Dual sales were originally credited. Other refunds use their jackpot and the fund for any shortfall. Completed draws and settled tickets stay unchanged. Cancelled future draws retain sales history and assigned public numbers; counters never go backwards.

The HTTP gate runs before Mini App authentication. The client fails closed if pause status cannot be loaded. Admin authentication remains available; its GET sessions filter draws/tickets and dated events to the selected economy epoch. Account balances remain current real balances. Archive writes are rejected by the server. Derived public player profile totals will be addressed before reopening, together with the still-unapproved bot-balance and other-game batches.

Only the three approved Fast jackpots are reset in batch 1. Other game economics and starter/bot amounts await the owner. See OD-058 for exact terms and the corrected PULSE 500,000-CAS tier.

## Reopening checklist for a later owner instruction

Do not run this section without an explicit instruction to reopen. Finish subsequent approved batches and review current player-profile projections and pending publication/notification queues. Preserve/cancel stale queued announcements through their normal audited lifecycle before resuming delivery. Invoke `EconomyTransitionService.resume` with an owner audit actor and an aware UTC timestamp; it requires no unresolved draws and persists `recovery_after`. Draw creation ignores cancelled reservations and uses the later of its last non-cancelled schedule anchor and this fixed checkpoint. An active slot has a unique partial database index; cancelled historical records may share its calendar time, but every public number remains unique and is never reused. Slots inside the planned pause are skipped. Uncreated slots have no assigned public number; existing cancelled numbers remain archived. Recovery after an actual failure later than the checkpoint remains chronological and idempotent.

The production compose override `K_LOTO_SCHEDULER_ENABLED=false` provides an additional operational stop while closed. Re-enable it only as part of that explicit reopening operation. Remove the planned-maintenance watchdog marker under the VPS operations lock after normal runtime monitoring and scheduling resume. Never remove financial history, reuse public numbers, truncate tables or reset sequences.
