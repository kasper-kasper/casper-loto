# Platform content events B

This release adds the nonvisual event stage to existing `Publication` drafts. The repository previously had A artwork/editor/manual publication, but no automatic A detector or channel dispatcher. B shares its persistence, revision/archive workflow, audit history and authenticated API; it does not introduce another publication store.

## Approved scope

| Type | Metric / source | Mode |
|---|---|---|
| B1.1 | Distinct registered `users.id`; Telegram and Web profiles linked to that ID count once | automatic |
| B1.2 | Purchased `tickets` plus `instant_tickets`, counting each purchased ticket once, including later-refunded purchase history | automatic |
| B1.3 | Completed `draws`, including all Fast and both completed Dual phases; instant games have no draws | automatic |
| B1.4 | Settled tickets with positive prize plus positive-prize instant tickets; a Dual ticket counts once | automatic |
| B2.1 | Current highest jackpot exceeding stored historical maximum; baseline uses completed draw snapshots, immutable jackpot wins and initial jackpot ledger peaks | automatic |
| B3.1 | Sum of all current jackpot accounts | draft on explicit request |
| B3.2 | Winning tickets settled during the current Moscow calendar day | draft on explicit request |
| B3.3 | Tickets, distinct purchasers, winning tickets, completed draws and per-game counts over an explicitly selected seven-day interval | draft on explicit request |
| B3.4 | Game(s) with the most purchased tickets in an explicitly selected interval; preserve ties, no winner for an empty interval | draft on explicit request |
| B3.5 | At least four immutable jackpot-win events in one Moscow day; one refreshable draft with all wins | automatic |
| B4.1–B4.8 | Owner-authored product-development events, exactly the eight requested types | draft only |

No winner names, user IDs or usernames are included in statistical payloads. Jackpot payloads include only game/draw/event IDs, CAS amounts and timestamps. Counts are read-only projections; no ledger or business history is changed.

## Configuration and collection

`backend/src/k_loto/application/publication_event_config.json` contains all thresholds, continuation rules, mode-independent future delivery policy and the 12:22 / 18:35 / 22:22 Moscow scan slots. It is package data and read per service invocation. Threshold grids are validated. Ticket/winning-ticket milestones continue by 5 million after 10 million; draws by 500,000 after one million. No infinite list is stored.

APScheduler reconciliation calls the application service, which claims the latest due slot under a PostgreSQL transaction advisory lock. Repeated workers/startups skip an already processed slot. On recovery, scan current authoritative cumulative totals and immutable win history: all crossed milestones are retained, not delivered as individual catch-up messages. `publication_event_states` stores counters/slot/record checkpoint. `publications.event_key` is database-unique and permanently retained across draft/published/archive, so an archived/rejected threshold does not reappear on the next scan.

Stable keys: `B1.n:milestone:<threshold>`, `B2.1:record:<integer CAS>`, `B3.5:day:<Moscow date>`. Every event has block/category/type/scope/mode/observed UTC time and structured payload. Record payload retains previous/new record, game/account IDs and timestamp. Record observations do not suppress a future A event for that game.

B3.5 is created at the fourth win, updated while draft, and has `ready_after` at the next Moscow midnight so a future dispatcher can include the whole day. Previously published/archived snapshots are never refreshed. The sparse immutable jackpot projection is rescanned to catch older recovered draws without a lossy time watermark. B3.1–B3.4 are never regular summaries; they exist only when explicitly requested.

## Separation and future dispatch

Automatic eligibility is distinct from editorial status and delivery. Both modes currently persist `status=draft`, `delivery.state=awaiting_content_and_visual`; no Telegram calls, images or player Stories are created. The manual visual editor/feed excludes nonvisual events. Attempting to publish or replace a nonvisual event through the existing visual endpoints is rejected. Archiving uses the existing endpoint/revision/audit workflow.

Future dispatcher policy: no daily limit; **30 minutes between automatic posts**, common pacing across A and B; manual posts bypass this limit and do not advance the automatic clock. `DeliveryPolicy.earliest` implements eligibility time calculation. It is not a running dispatcher. A grouping remains per draw; B achievements found in one scan share `B:scan:<slot>` and can form one B publication. `combine_blocks=false`: never mix A and B into one post. Actual rendering, delivery claims/acknowledgements, text composition and the A detector remain separate future work; do not enable sends merely because an event says `automatic`.

## Owner API

All endpoints use existing admin authentication; writes also require existing CSRF.

- `GET /api/v1/admin/publications/event-types`: exact B type registry and nonsecret configuration.
- `GET /api/v1/admin/publications/events`: cursor-paged nonvisual drafts (existing publication view plus event metadata).
- `POST /api/v1/admin/publications/events/scan`: owner-triggered reconciliation, still deduplicated and delivery-disabled.
- `PUT /api/v1/admin/publications/events/<UUID>`: idempotent B3/B4 draft creation. `event_type`, optional bounded text `fields`; B3.3/B3.4 require aware UTC `period_start`/`period_end`. Response ID is the requested UUID; conflicting retries are rejected.
- `POST /api/v1/admin/publications/<UUID>/archive`: existing archive/revision workflow.

An admin UI for these nonvisual drafts is not added in this backend-only phase. The later content/visual adapter should expose these APIs to the owner and connect selected event payloads to templates without changing immutable event keys/history.
