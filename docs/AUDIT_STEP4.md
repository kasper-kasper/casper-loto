# Audit step 4 — Mini App runtime, 2026-10-14

## Implemented

| Confirmed issue | Change | Evidence |
| --- | --- | --- |
| Instant tickets and admin audit could be changed/deleted | Immutable PostgreSQL triggers | Real UPDATE/DELETE rejection in disposable PostgreSQL |
| Purchased Dual ticket could be reassigned to a second draw; first-round result could be overwritten | Protect second_draw_id, id/source and committed round matches | Real SQL rejection, legitimate two-round payout/replay still passes |
| Two draws could share one lottery time slot | Unique lottery_id/scheduled_at constraint | Production preflight: zero duplicates; concurrent preparation creates one draw |
| Admin could invalidate fixed Dual terms | Service validation and SQL price/shape/jackpot guards | Invalid API-service settings and direct SQL are rejected; valid payout preserved |
| Lost Telegram acknowledgement caused automatic replay | UNCERTAIN, interruption quarantine, attempt fencing | Parallel claims, stale acknowledgement and interruption recovery tested without Telegram |
| Permanent Telegram refusal retried indefinitely; rate limit ignored | Definitive rejection cancels, 429 uses retry_after | Dispatcher regressions and actual outbox timing |
| Queued delivery ignored current consent/inactive profile | Recheck at claim immediately before formatting/send | Revoked-consent fixture sends nothing |
| Instant buyer received inactivity invitation | Both draw and instant purchases define latest activity | Actual PostgreSQL engagement check |
| Archived uncertain publication blocked all posts | Only active drafts block; archive cancels with audit | Actual JSONB queue resumes after audited archive, with fake transport |
| Crashed channel delivery stuck forever; malformed artwork blocked next item | Stale sending becomes uncertain; pre-network failure becomes failed | Focused tests and real interrupted-claim smoke |
| One failed lottery stopped every recovery | Isolate its later draws until next retry, continue other lotteries | Failed first draw stays pending; other lottery completes |
| Initial recovery/bootstrap schedule failure prevented API startup | Keep diagnostics/API available and install retry jobs | Startup and bootstrap regressions |
| Partial recovery appeared successful or hid progress | Failed heartbeat, partial counters, no new auto-play/reminders in partial cycle | Heartbeat regression |
| Production bot still advertised retired Web entry | WEB_ENABLED=false for bot and conditional command | Disabled-command regression; production retirement health check |

## Operational behavior

An uncertain Telegram result is retained without automatic retry. This deliberately favors avoiding duplicate messages over guaranteed delivery when no acknowledgement is available. Other private messages continue. For channel publications, inspect the actual channel before using the existing archive action on the uncertain draft. Archive records the previous outcome and frees the queue; it does not delete the Telegram post or send it again. An active attempt is protected for five minutes; an interrupted attempt can be archived even when transport is disabled.

Dual mechanics, payout amounts and odds are unchanged. The migration never repairs balances or rewrites completed history. A conflicting existing account or duplicate schedule blocks publication and requires investigation.

Production migration adds a persisted notification state. API and bot are briefly stopped after candidate checks/log capture, migrated and restarted together to avoid old workers decoding the new state. Database/gateway remain running during preparation. Local Web sources are retained, excluded from publication and not rebuilt by this step.

## Validation and release

See the current DEVLOG entry for counts, candidate PostgreSQL results and production verification. Disposable checks copy schema plus Alembic revision only; they never copy player/business data. Current known fresh-empty migration bootstrap limitation from stage 1 is unchanged; release checks start from the actual deployed schema.
