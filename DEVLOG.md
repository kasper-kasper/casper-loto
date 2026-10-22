## [English-first GitHub presentation and private publication preparation] - 2026-10-23

Owner authorises the first private GitHub upload and revises target dates (OD-080). README.md is now English; README.ru.md retains the personal Russian text. Roadmap and documentation index have the same English/Russian navigation. Voting is split from the lottery builder; owner targets transparency Oct–Nov 2026, profiles Nov, season launch/voting Jan 2027, cooperative goals Feb–Mar, API May and builder summer. English social cover uses the unchanged approved logo/palette with “Luck costs nothing” / “Give it a try”; Russian cover/layout retained. Repository kasper-kasper/casper-loto created as Private; owner completed GitHub/Git Credential Manager sign-in. Local publication preparation preserves full source history, excludes secrets and unrelated output, and uses source/Git backups before committing/pushing. Prior 949-backend/319-frontend checks remain applicable: no runtime source changes; frontend source/artifact hashes reverified. Both language layouts and navigation checked at 320/390/1280px in light/dark. No licence assigned, public exposure or VPS release.

## [Personal README, roadmap and GitHub readiness audit] - 2026-10-23

Revised Russian README into the owner's own voice, added UTC+3, Best regards / Andrey Kasper, and a clearer server/SystemRandom explanation. Removed the contact-language restriction. Roadmap covers next-generation profiles, transparency, roughly three-month free seasons without daily-login pressure, cooperative goals, player lottery proposals/voting and a public API; dates through 2027 are proposals for owner review (OD-079). Added publication checklist and refreshed readiness report. Prepared a 1280x640 GitHub social image from the unchanged approved logo/palette; all nine brand-pack images present. Excluded unrelated output/ documents from Git/Docker, preserved files and archives; completed videos were already ignored and absent from reachable history. No broad filesystem/Git cleanup.

Audit: about 60 MiB of prospective files, 393 commits; 5,705 reachable blobs and 831 then-current files scanned without current-secret or known token/key matches. No historical real .env/key/dump paths or files over 50 MiB. Git connectivity fsck and local documentation links passed. Two pre-existing failures came from test Lottery objects missing ruleset_code; corrected only those objects. Final clean Python environment from uv.lock passes Ruff/format/MyPy and runtime manifest (67 locked distributions); full backend with a fresh disposable PostgreSQL 16 database: 949 passed, one Windows symlink skip. Migrations through 0067 and alembic check passed. Clean npm installs: Mini App 251 tests, Admin 68 tests, both typecheck/lint/build and source/artifact hash checks pass. Existing Vite large-chunk warning remains non-blocking. CI now supplies a separate achievement template DB so PostgreSQL scenarios run; YAML parses and official v7 action tags resolve. GitHub-hosted Linux execution and final committed clean-clone verification remain prepublication steps. Temporary database container stopped/auto-removed; preview database and product runtime unchanged. Local GFM preview verified at 320/390/1280px in light/dark. No production release, version bump, GitHub push or assigned licence.

## [Russian GitHub README and author story] - 2026-10-23

Prepared the owner's requested Russian README for review: unchanged approved logo, exact five iPhone PNGs, responsive screenshot links, Telegram entry/channel/author contacts, navigation, existing technical documentation and a personal author story. Main slogan approved as «Удача ничего не стоит», with «Просто попробуй» as invitation. Game RU/EN support is distinguished from this Russian-only document. Added a public roadmap separating released features from undated ideas. Removed stale language/achievement plans, invented GitHub links and the draft's unapproved MIT promise. Brand guidance and OD-078 record the owner's statements and remaining decisions. Verification: local Markdown/image links and heading anchors resolve; all three supplied Telegram URLs returned HTTP 200; five copied image hashes match originals. Local GFM preview checked in light/dark at 320, 390 and 1280px with no page overflow or broken images; disclosures and author anchor work. Reports/screenshots under .tools/readme-review. Documentation/assets only; no product release, version bump, GitHub push or VPS deployment; runtime suites not applicable.

## [English Mini App 1.70.0 — production verified] - 2026-10-23

Published scoped snapshot ba6d8df after clean Mini App typecheck/lint/build and all 251 tests in 35 files. Existing cross-window cart test now waits for persistence as well as the UI update. RU/EN browser QA at 320×568/390×844, including New Year picker/result, passed without overflow; no persistent purchases. Exact baseline bytes retained for unrelated sources and the existing Admin build verified. Local source backup, remote database backup, gateway candidate, public HTTPS/hash/auth, independent monitoring and backup catalog gates passed under the operations lock. Only gateway recreated; API/bot stayed running. Evidence: docs/MINIAPP_LANGUAGES.md and archive/local/2026-10-22/miniapp-en-release. The published snapshot remains immutable; this completion report is local evidence.
## [Mini App English localisation] - 2026-10-22

Mini App 1.70.0 adds RU/EN message dictionaries across all player screens, all 93 achievement definitions and collection copy, and historical system notification presentation. Explicit per-account device choice overrides Telegram language, then browser/device language; unsupported languages use English. Locale changes re-render existing screens through LanguageRoot without remounting state or reissuing purchases. Integer CAS, API identifiers and Moscow schedules remain authoritative and unchanged. No backend/schema changes. Regression coverage includes priority, storage failure/account isolation/window sync, state preservation, exact amounts/timezones, source-message/placeholder coverage and an actual account/catalogue/picker RU → EN → RU flow. Isolated gateway release uses the existing locked backup/hash/health sequence. Full verification and publication evidence: docs/MINIAPP_LANGUAGES.md.

## [Draw UI compact Telegram layout and standard purchase tools] - 2026-10-22

Frontend-only Mini App 1.69.1. New Year restores common quick purchase/five-draw/favorite UI, symbol favorite previews and safe-area-aware four-row field sizing. Shared services unchanged. Audited all draw screens: normal games use common composer; Bingo already has quick card buys and favorite-number search; Dual retains one paired draw and now exposes its already-supported favorites. Seasonal catalog card owns a full row with a single full-bleed photo and lower gradient after owner rejected the side-by-side split. 47 focused UI tests, NewYear follow-up 11, typecheck/lint/build and mobile 320x568/390x700/844/430x932 checks. No backend/full-suite rerun. See docs/DRAW_UI_2026-10-22.md.

## [Two lotteries — production verified] - 2026-10-22

Published isolated snapshot 2706fbf: backend 1.59.0, Mini App 1.69.0, migrations through 0067. All candidate migration/financial/fresh-schema gates, restart, public hashes/auth and monitoring gates passed. Both lotteries active with five scheduled draws each; initial Mini jackpot ledger entry exactly once. 16 public game assets/chunks verified, zero monitor warnings, economy open. Detailed final evidence: docs/LOTTERY_RELEASE_2026-10-22.md and archive/local/2026-10-22/lotteries-release-retry. Published candidate remains immutable; this completion report is local release evidence.

## [Two lottery production release preparation] - 2026-10-22

Owner authorizes publishing Mini and New Year with focused checks. Isolated candidate starts from the exact current VPS source manifest (zero source mismatches), overlays only the two games and increments backend/Mini App to 1.59.0/1.69.0. Tests: 34 new-game cases including 7 PostgreSQL scenarios; 127 shared-engine/API/schedule/notification regressions; 37 affected frontend cases. No whole-project suite at owner request. Migration restore check permits only the new accounts and Mini initial ledger credit; fingerprints all old financial history and achievement runtime and repeats migrations. Standard locked backup/candidate/recovery release flow remains in place. See docs/LOTTERY_RELEASE_2026-10-22.md.

## [New Year 2027 — paper receipt and disclosure, local only] - 2026-10-21

Owner requested only the rules spacing and receipt refinement; catalog inspected without changes. Rules now use the shared ticket-options disclosure pattern: explicit 22px separation from the paper strip, quiet summary/plus, framed content only when expanded. Receipt is one aged cream paper surface with burgundy typography, double-line border and lightweight SVG engraved fir sprigs. Removed the solid burgundy masthead. Close control has an explicit 32px button/16px icon, zero padding and consistent right alignment in portrait/landscape.

Focused checks: 9 NewYear UI tests; Mini App typecheck/lint/build. Mobile browser: pending/result receipts at 320x568 (408.89/516.89px, no overflow), result at 568x320 (292px, no overflow); close icon centered with 0px delta and closes correctly. Rules expanded/collapsed in the real local app. Temporary receipt-only fixture removed; no purchases or backend changes. Local only.

## [New Year 2027 — visual corrections, local only] - 2026-10-21

Replaced the 400% room-image crop with a dedicated fine walnut texture. Source-window clipping prevents neighbouring atlas objects from bleeding into the postcard, receipt and narrow slots; separately generated champagne and sparklers share the same assets across game surfaces. Catalog/home use a cohesive static still life instead of three enlarged sprites. Ivory titles, pale gold year and restrained shadow; compact receipt has a burgundy masthead and cream body. Built-in image_gen asset paths/prompts are recorded in `frontend/miniapp/src/assets/newyear/manifest-v2.json`.

Purchase notices now render in a fixed overlay for this game, preserving the field and environment dimensions. Bulbs/candle overlays anchor to the original room image aspect ratio, animate only opacity/transforms and respect reduced motion. Fixed shared motion-budget resume after visibilitychange without requiring another IntersectionObserver event; offscreen scenes remain paused and removed nodes are unobserved.

Focused verification: 21 tests (NewYear, TicketComposer, performance), Mini App typecheck/lint/build. Browser checks: real holiday catalog, picker and waiting broadcast; isolated home/receipt/revealed symbols and mock purchase without API/ledger mutations. Before/during/after notice: field y=316.15, scene height=873.15, scrollY=0 unchanged. Receipt fits 320x568 (pending 410.49px, result 518.49px) and 568x320 (292px), no internal overflow. Bulb opacity and flame transform change between samples. Temporary visual fixture removed. No backend/full-suite run, production publication or persistent test purchase.

## [Casper Mini — independent visual identity, local only] - 2026-10-21

## [New Year 2027 — local only] - 2026-10-21

Added `newyear2027` using the existing transactional purchase, scheduling, recovery and settlement services. Owner confirmed daily 21:15 Moscow, cutoff 2 minutes and an indefinite series until another instruction; delegated economy routing and allowed burning. Ticket 10,000 CAS, 3 distinct IDs out of 12, cumulative 101 tickets/player/draw, no progressive allocation. The shared rule strategy now supports an optional fixed shared prize: 5,000 for one match, 30,000 for two, exactly 1,000,000 shared by full-match tickets in public-number order. All payouts remain fund-backed and ledgered. Zero compatibility accounts; no jackpot issuance, reset, carry or jackpot-win news. Migration 0067 adds independent identity/counters and zero accounts. Admin guards reject progressive configuration and distribution designation for this game.

Created a transparent 12-item atlas and room plate with built-in image_gen; compressed WebP and exact prompts/provenance live under `frontend/miniapp/src/assets/newyear`. Separate interactive symbol grid, cream/red paper strip and receipt, holiday catalog/home cards, symbol live/replay/archive and notification names. Individual CSS bulbs/candle flame use calm opacity/transform animation; reduced motion and existing scene budget apply. No persistent animation of all game objects and no new renderer dependency.

Validation limited by explicit owner request: 13 focused backend tests (3 disposable PostgreSQL scenarios), 18 UI tests for new game/shared composer, affected Python Ruff and Mini App typecheck/lint/build. Only the 8 New Year UI cases and build rechecked after final presentation changes. Receipt PURCHASED/SETTLED fits at 320x568 without internal overflow; settled landscape fits 568x320. Actual local catalog, picker and waiting live screen visually reviewed. Synthetic receipt/home QA fixture removed. No test purchases in the persistent preview DB. Backed up and migrated only loopback test/preview DBs, restarted the local preview. No production deployment, full suite, admin frontend build or existing-history reset. See `docs/NEW_YEAR_2027.md` and `.tools/newyear-2027`.


Owner rejects recolouring the shared classic coupon and the scrolling receipt.
Add dedicated MiniHeader/MiniCoupon, engraved cream paper, dimensional enamel
number seals and layered emerald lighting/contour background. Draw a reusable
four-leaf jewel in SVG (gold setting, faceted enamel, veins and central stone),
replacing all Mini drum artwork in header, catalogue, home next-draw feature and
live/replay scene. Other games retain their artwork and picker components.

Receipt uses a viewport-height grid capped at 650px, flexible five-row number
field and compact result/footer. Short portrait and landscape layouts preserve
all 30 numbers, six chosen numbers, status, result and cost without clipping or
internal scroll. Lock background scrolling while the receipt is open.

Checks are intentionally frontend-only: 16 focused Mini/Today tests pass; affected
frontend typecheck/lint/build. Browser QA verifies real local picker, random fill,
catalogue and the Mini home feature. Temporary isolated visual fixture checks
PURCHASED/SETTLED at 320x568, 360x640, 390x844 and 568x320: all eight fit the viewport,
receipt/grid overflow zero. Fixture entry files removed after QA; screenshots and
measurements retained in .tools/casper-mini-v2. No backend suite, economic edits,
database migrations, clean-install checks, admin rebuild or VPS publication.

## [Casper Mini — local implementation] - 2026-10-21

Owner requests local-only permanent Classic 6/30, exact 10,000 CAS ticket,
20,000,000 CAS base, 40% contribution, 100/500 caps and Moscow 10:30/19:15 slots.
Add independent mini/casper_mini_6_30 identity and data migration 0066, with new
accounts and ledgered opening jackpot, preserving all old history and epochs.
Reuse transaction locks, draw snapshots, purchase receipts, settlement/reset,
schedule recovery, notifications and reporting. The 100-ticket cap includes all
five draws in a prepaid purchase. Mini gameplay is skipped by achievement
projection; wallet game counters exclude Mini, actual wallet balances stay true.

Reference-inspired emerald/cream/gold coupon, 30-number field, receipt and
classic broadcast share existing picker controls and partial live highlighting.
Add server-fed prize table and complete rules, catalogue identity, local design
fixtures and responsive CSS. Local preview/test databases backed up before
migration under .tools/casper-mini/backups; no production access or publication.
Validation: 21 Mini backend tests pass including four real PostgreSQL scenarios
(limits/concurrency, idempotency, five draws, settlement/notifications/achievement
exclusion). Full backend suite: 935 passed, one skipped (Windows host cannot
create a symlink for the Linux-only maintenance retention regression), no
failures. Mini App: 216 tests in 33 files, including nine Mini tests; Admin: 68
tests in eight files. Both clients pass clean-install typecheck/lint/test/build;
backend mypy, ruff and format pass. After mobile QA, fix lazy stylesheet priority
so the Mini quick controls, checkout and entire live stage stay emerald, and
retain the Mini Classic header when switching to live.

Real loopback browser smoke at 390x844 and 320x720 verifies selection/removal,
one completed test purchase, Mini-filtered tickets and receipt, six selected
balls, thirty-number field and live waiting. Exactly 10,000 CAS debited and
4,000 CAS added to Mini jackpot; test ticket #0001 remains in local history.
No horizontal overflow. Screenshots: .tools/casper-mini/picker-390.png,
receipt-390.png and live-390.png. Preview API/database health is ok, five Mini
future draws prepared. Final Mini clean rebuild and both client source/artifact
hashes verified. Additional focused Mini/live tests pass (15); parallel App
recheck had one existing catalogue-loading timeout during a concurrent build,
then the isolated complete App file passes 46/46 without source changes. Final
lint/typecheck/build pass. Source snapshot and test logs retained privately under
.tools/casper-mini. Production, VPS and existing economic launch state were not
touched.

## [Remove maintenance styling from startup] - 2026-10-21

Owner still observed the maintenance splash after the earlier text correction.
Use the existing app Skeleton during the availability check; the maintenance
layout is mounted only for a confirmed pause or connection error. Mini App HTML
and version response use no-store; hashed assets retain immutable caching.
Frontend-only patch 1.68.2, API/bot unchanged at 1.58.2. Focused gate regression,
affected frontend typecheck/lint/build and startup browser smoke only; no broad
backend/database tests or API/bot restart. Three gate tests, Mini App typecheck,
lint and clean production build pass. Browser smoke holds the status response
at 390px: regular skeleton present, maintenance layout absent both while waiting
and after opening, no horizontal overflow. Gateway-only publication completed
at 02:08 Moscow, with backup/operations lock, Caddy validation and public health/
hash/auth checks passing; monitor warnings empty. API/bot uptime preserved.
Post-publication mobile browser smoke on the actual public URL verifies version
1.68.2, HTML no-store and zero maintenance layouts while checking and after
opening. Owner can reload an existing Telegram tab with its Update button.
Read-only preflight also confirms achievements activated automatically at
02:00:01.857 Moscow and remain unpaused; this frontend patch changes no runtime
or financial state. Source snapshot and verified archive retained privately in
archive/local/2026-10-21/startup-skeleton-release.

## [Owner digest clarity and neutral Mini App startup] - 2026-10-21

Replace the checking-state economy-maintenance headline with neutral loading;
real pauses and network failures still keep gameplay unmounted. The public open
status no longer advertises an economy update. Regression covers a deferred
status response, confirmed pause, failed connection and runtime pause event.

Owner requested a readable daily report after inspecting the actual delivered
20 October digest. Classify tickets using authoritative FAST codes and one row
per purchase (Dual counted once). Paid gross purchases match purchase ledger
flows; gifts and later refunded tickets are separate. Count distinct buyers
across draw and instant tickets, newly registered Telegram players within the
same Moscow/epoch interval, and current player/jackpot account totals. Add a
separate ledger achievement-reward metric; preserve existing Admin other-credit
semantics. Report actual operation-net issuance/burning, multiple factual
warnings and observed net fund expense with a readable long-horizon estimate.
No economy changes, new background loops, schema changes or resend of delivered
reports. Durable achievement launch schedule remains untouched.

Validation: full required backend 913 passed, one Windows symlink skip (covered
by the Linux release candidate); Mini App 207 passed, clean typecheck/lint/build,
Ruff/format and strict mypy 112 sources pass. Real PostgreSQL checks date/epoch
boundaries, FAST/instant/draw separation, gifts, refunds, distinct buyers and
Dual's single purchase. Ledger tests prove funded achievement rewards are not
issuance. Mobile browser smoke at 390px holds the status response, confirms no
maintenance copy during loading, then opens the app without horizontal overflow.
Published API/bot 1.58.2 and Mini App 1.68.1 at 01:37 Moscow; Admin stays
1.61.2 and schema stays 0065. Standard operations lock covers backup, exact
snapshot upload/build, full production restore/history fingerprint verification,
76 Linux candidate tests (including symlinks), financial/integration/profile/
retirement smokes, empty DB recovery, diagnostic archive, selected restarts and
public HTTPS/hash/auth/independent health checks. All pass; monitor has no
warnings. Snapshot 70f7107, 649-file verified source ZIP v3 and rollback archive
release-before-1792535719018629690.tar.gz retained privately. The initial local
artifact guard caught clone checkout line-ending differences before any SSH
publication; restoring the exact tested frontend bytes resolves it.

At 01:38, an explicitly READ ONLY production transaction renders the new digest
without queuing/sending anything: previous day 16,530 paid tickets = 15,895 FAST
+ 0 instant + 635 ordinary draw, 10 distinct buyers and 0 new Telegram users.
Gross purchase/prize/burn/issuance totals match the delivered report. Public
maintenance status is open with no stale message. All 93 definitions remain
prepared, unstarted/unpaused, worker/scheduler enabled, original 02:00 Moscow
schedule preserved. New copy applies to the next normal daily report; delivered
messages remain untouched.

## [No-wait launch barrier follow-up] - 2026-10-21

Published API/bot 1.58.1; Mini App remains 1.68.0, schema 0065 and the original
02:00 Moscow schedule preserved. Latest full required backend run: 908 pass,
one Windows symlink skip; Linux candidate 76 tests and financial/integration/
empty DB smokes pass. Full prepared production restore preserves all history
fingerprints and runtime schedule, public hashes/auth/health pass. A Debian 502
failed one candidate build before production changes; unchanged retry succeeds.
At 01:04 Moscow, prepared backup + explicit live verification confirm 93
definitions, zero awards/unlocks/local test users, disabled/unstarted, scheduled
23:00 UTC, worker/scheduler enabled, no worker errors. Snapshot e3e5d55 and
verified 648-file source ZIP v3 retained in the private archive. No GitHub work.

Final overlapping-source test reproduced a 2.07s activation wait on a busy
balance-table write. Add NOWAIT to the atomic source barrier: failed acquisition
rolls back the whole launch immediately, releases partial locks and yields to
ongoing gameplay; next scheduler tick retries. New PostgreSQL regression checks
fast deferral, unchanged unstarted state and successful later activation.
API/bot patch 1.58.1 leaves catalog, rewards, frontend and durable 02:00 schedule
unchanged. The full-restore verifier now preserves an already prepared runtime
instead of assuming an initial empty catalog; history digests stream in bounded
batches and engine disposal stays on its owning event loop.

## [Achievements published and 02:00 Moscow launch armed] - 2026-10-21

API/bot 1.58.0 and Mini App 1.68.0 published; schema 0065. Full production
restore migration/catalog verification preserves financial/history fingerprints;
76 Linux candidate tests, financial/integration/profile/recovery/retirement
smokes, empty bootstrap/index recovery and schema checks pass. Exact public
client hashes/auth boundaries and independent health pass, no worker errors.
After all gates, schedule persisted for 2026-10-21 02:00 Europe/Moscow
(2026-10-20 23:00 UTC); verified at 00:40 Moscow still disabled/unstarted,
93 definitions, zero awards/unlocks/local fixture users. Back up prepared state
under operations lock; database/source rollback and diagnostic archives retained.
Initial package omitted frontend image recipes; it stopped before production
changes, corrected source inventory and successful repeat recorded. Clean source
snapshot commits 6c965eb/e8d62e0 preserve owner worktree; no GitHub publication.
Source ZIP 648 verified files, SHA-256 and logs retained in private local archive.
Actual timed activation remains future and is monitored on server; notebook is
not required. Details in ACHIEVEMENTS_PRODUCTION_RELEASE_2026-10-21.md.

## [Achievement production launch preparation — owner authorized] - 2026-10-21

OD-076 authorizes publication after final checks with achievement tracking kept
disabled until 02:00 Europe/Moscow, 21 October. Migration 0065 adds a durable
scheduled time/catalog revision and processing-only emergency pause. Guarded
production CLI validates and imports exactly the approved 93 entries, rejects
past/naive start times, fixture awards, double starts and changed catalogs.
The existing scheduler checks the singleton and establishes the once-only UTC
boundary with a short transactional source-write barrier at activation. No
long maintenance window, no local data transfer or historical reward replay.
Pause stops work while capture stays enabled; cancellation is prelaunch only.
Runtime monitoring reports ready work, lag, exhausted events and overdue start.
API 1.58.0 / Mini App 1.68.0. Release verification/results are recorded in
docs/achievements/ACHIEVEMENTS_PRODUCTION_RELEASE_2026-10-21.md.

## [Compact profile heading and category titles — local only] - 2026-10-21

Remove the large duplicate «Моё» heading; keep a semantic compact «Личный
кабинет» h1 and reduce header height from 59 (+4 margin) to 45px. Preserve
the notification button and bottom navigation. Balance and following blocks
move upward by 18px. Remove ticket delivery/limit/waiting explanations and
verbose case activation footnotes from shared achievement presentation; retain
actual condition descriptions. A subsequent owner instruction hides all case
information in the UI while preserving reward configuration.
Shared achievement title component applies Cormorant Garamond 600 in the
badge's gold, with distinct Prata 400/platinum for «Каспер, подвинься», across
cards, details, profile summary, notices and master collection previews.
Extend the same title font to uncommon/rare/epic with their existing category
colors; keep common typography unchanged.
Self-host four Cyrillic/Latin WOFF2 subsets (68,768 bytes total) with SIL OFL
licenses, font-display swap and local fallbacks; no runtime third-party font
requests. Backend rules, rewards and fixtures unchanged. Mini App lint and
typecheck/build pass. App/achievement/collection focused run: 60 pass; final
case-hiding/category-color update: 14 affected tests pass. Initial concurrent
build/test run had one catalog wait timeout; sequential focused run passes.
Browser smoke at 320/390px confirms compact h1, all category fonts/colors,
ordinary titles inheriting prior style, exact title/emblem platinum match,
loaded local fonts, no case/delivery copy or horizontal page/dialog overflow.
No VPS or GitHub publication.

## [Legendary visual unlocks for the laptop account — local only] - 2026-10-20

At the owner's request, unlock all eleven legendary entries and thirteen
collectibles (eleven badges, two themes) for isolated preview Telegram ID
900000002. Back up the preview database first. Explicit visual-fixture award
and reward status `preview` preserves catalog reward descriptions while keeping
CAS/ticket/case parts outside processing queues. Grant cosmetics through the
existing application adapter; retain current cosmetic selection and all other
progress. No invented jackpot results, ledger movements or ticket purchases.
The isolated helper refuses other environments/databases/users and leaves an
audit correction identifying the visual fixture. Repeated execution adds zero
duplicates. Verify eleven awards, thirteen unlocks, unchanged balance/tickets
and the authenticated read API. No application code or production changes.

## [Legendary achievements, compact gifts and collection — local only] - 2026-10-20

Owner approves the ten jackpot entries and final «Каспер, подвинься», raising
CAS to a 40m floor, matching-game gifts 100–500, ordinary future cases 20–100.
Final allocation 40m–350m: base total 1.13bn CAS, 2,825 gifts, 565 future cases.
Fixed-ten final awards 1bn CAS, 300 of each ten games (3,000), 200 ordinary
future cases, unique platinum/gold badge and «За гранью». No legendary cases.
Catalogue now 93. Preserve prior categories/rewards, epoch and immutable snapshots.
Explicit exact result filters fence legacy CODE/PULSE/other formats; Bingo <=28
and natural payout required, technical distribution and Dual excluded.

New earned_set validates fixed IDs/cycles, initializes once at management import
and advances only on dependent awards. New ticket_pack stores one entitlement,
issues one standard funded ticket per transaction and lazily records deterministic
child parts. Existing unique Ticket reward references remain. Parent reads use
the existing (award_id,position) index with root positions <16, independent of
the number of issued children. Yield/retry between units; no synchronous 3,000
ticket loop in gameplay/HTTP reads. Extend existing gift whitelist to three FAST
codes; retain ordinary purchase accounting/RNG/caps. Extra gift-only ceiling is
outcome-space minus one (and finite Bingo pool minus one). All final packages
300 are below combination coverage; occupancy/per-draw limits spill to future
eligible draws. Missing fund/draw/season stays waiting without substitution.

Migration 0064 adds parent/progress fields, sparse immutable cosmetic unlocks and
opt-in preferences with composite ownership FKs. Gold unlock is once, choice is
never automatic. Authenticated collection GET/PUT delegates to application rules;
unknown/locked/wrong-slot choices and client grant fields rejected. Add profile
collection, selected badge, two private themes, locked-item/theme previews and
actual approved Casper artwork/wordmarks; no heavy renderer/dependency. Batch
selected_badges projection is ready for future rankings (no ranking UI exists).

Checks: 894 backend pass in corrected full run, one Windows symlink skip, two
previously passed expensive load tests deselected on repeat; new HTTP test also
passes separately, total 897 unique successful checks. Final legendary suite
22 passed. Early full-run failures came from disabled editorial mock flag, one
unknown-cosmetic error expectation and retired fixture paths; test-only setup
now mirrors conftest opt-in, compiler test reads local archived libraries and
skips when that private archive is unavailable. Runtime publications stay off.
Mini App 206 / Admin 68 tests pass; parallel UI timing failures under load pass
in full single-worker rerun. Full Ruff/format/mypy and both client builds/lint
pass; Alembic check clean. Browser 390/320 verifies profile 15/93, legendary 0/11,
1bn/ten 300-packs/200 cases, collection and full-color previews without fake grants.
No JS errors or horizontal overflow; local event errors 0, actual unlocks 0.

Pre-change preview/test/fresh dumps and SHA-verified source archive stored under
archive/local/2026-10-20. Docs index, exact reward/cap table, report and OD-075
updated. No VPS deployment, GitHub upload, fabricated local awards, resets or
changes to ticket prices/jackpots/winnings/probabilities. Case issuance/opening
and separately authorized production activation remain future stages.

## [Workspace organization and GitHub readiness — local only] - 2026-10-20

Owner requested a reversible folder cleanup, documentation organization and a
GitHub readiness assessment; no upload/deployment was requested. Created archive
with reference sources and ignored private local evidence. Moved retired Web,
channel/stories designs/media/builders, old Grand/Halloween variants, .tmp,
browser evidence, 207 one-off helper scripts and historical .tools artifacts.
570 move records preserve 66,120 accessible files / 2,178,719,650 bytes; SHA-256
checked 12,079 files before/after, excluding installed dependencies and caches.
Directories are moved whole; inaccessible old test-cache children remain inside
the archived directory rather than being deleted or having permissions reset.
24 documentation/catalogue files reorganized: 16 achievement docs/JSON files in
docs/achievements, eight historical docs alongside archived features. Repaired
links and the active preview catalogue path. Runtime tools, .env, local DB,
backups, .maintenance, active app sources and immutable financial history stay.

Retired publication assets and archive/local are ignored; all archive content
is excluded from Docker/git archive/VPS releases and rejected by release-snapshot
validation. Legacy Web source stays available for local Git history/reference.
Updated root README; added docs index, folder map and GitHub readiness assessment.
Known existing business changes were not staged, committed, reverted or pushed.

Read-only Git audit: 401 commits, 12,700 reachable blobs; no exact current .env
secret matches, no tracked historical .env/private-key/dump paths, no files over
50 MiB. Five token-like JPEG matches are verified standard DHT Huffman bytes;
historical object hashes match those same images. Connectivity fsck passed.
Audit is preliminary, not a guarantee concerning unknown historical secrets or
personal information. No remote is configured. Recommend private GitHub first;
review/commit accumulated changes and run full release checks before upload.
Existing GitHub CI needs explicit achievement test database wiring: opt-in
PostgreSQL tests currently skip without ACHIEVEMENT_TEST_DATABASE_URL.

Passed 38 focused release/snapshot/editorial-retirement/launcher checks, Ruff and
format for affected scripts/tests, both client TypeScript/builds, isolated preview
setup with preserved epoch/progress, 15-document link check and browser smoke
(profile 15/82, epic 0/17). No gameplay, CAS, draw rules or VPS state changed.
Private move/audit manifests and organization source ZIP live in
archive/local/2026-10-20. Full unrelated project suite was not rerun for this
non-release organization task; future publication still requires a clean check.

## [Epic achievements — implemented locally] - 2026-10-20

Owner approved the 17 epic entries and interpretations, raising CAS to 3m–8m
and 20m for 100k paid tickets; five adjacent winning draws award ten Grand
tickets. Announced four planned cases on fifteen entries, one on Big Collection
and Human Orchestra. Final totals: 98,500,000 CAS, 165 gifts, 62 planned cases.
Added epic catalogue/CLI/preview and violet outline artwork; shared catalogue 82.
Bounded matches_any filter combines mixed Dual results into one counter. Adjacent
completed draw checks inspect up to four neighbours each side and saturate at
five. Revision-3 management replay rebuilds derived post-launch win projections
without duplicating purchases/day counts or losing a partial draw cursor.
Existing categories, launch epoch, immutable history and award snapshots remain.
No physical schema change; Alembic check confirms no upgrade operations.

Passed 144 focused backend checks and 14 UI tests, Mini App typecheck/lint/build,
Ruff and targeted mypy (six modules, follow-imports=silent). Unrelated existing
launcher type errors were not changed. Browser verified 390/320px, 17 epic cards,
filters/details, 10 Grand and four-case text, six-digit badge, profile 15/82 and
no horizontal overflow or JS errors. Local worker has zero failed events and
projection revision 3. Original local progress retained; no fabricated awards.
Saved local pre-epic DB dumps and verified explicit source ZIP without secrets.
Updated OD-073 and final reward table; details in
docs/achievements/ACHIEVEMENTS_EPIC_LOCAL_REPORT.md. No VPS publication, per owner request.

## [Epic achievements — reward proposal only] - 2026-10-20

Owner supplied 17 epic entries and asked whether rewards should be more generous.
Prepared docs/achievements/ACHIEVEMENTS_EPIC_PROPOSAL.md and pending OD-073: 2m–15m CAS,
75,500,000 CAS total, 160 gift tickets/cards and seventeen single planned cases.
Read current local rules/registry and active local IDs: Ball 5+0, Grand 5+0/5+1
are valid; 11 draw games plus three instant games make the exact 14-game goal
possible. Preserve prior Ball identity and CODE four-of-five interpretation.
Explicitly propose combining the two eligible Dual results toward three wins.
No catalogue/schema/runtime/reward changes or tests for this documentation-only
proposal; existing common/uncommon/rare conditions stay intact.

## [Rare achievements — implemented locally] - 2026-10-20

Owner approved the 20-entry rare proposal and interpretations, raising CAS to
400k–900k. Final rare totals: 12,300,000 CAS, 80 gift tickets/cards, ten planned
one-case rewards. Added rare catalogue/CLI/preview integration and blue outline
artwork, retaining common/uncommon conditions, immutable awards and epoch.

Migration 0063 adds a winning-ticket count to existing sparse player/draw rows.
The worker caches/upserts each player/draw per page, derives maximum wins in one
draw and checks at most two completed neighbouring draws on each side for a run
of three. Daily FAST uses the saved daily lottery set. Full-card Bingo reads
all three saved row-closing moves, while CODE remains four of five equal positions.
Repeated results reuse existing filtered counters and distinct paid ticket events.

Management projection revision 2 rebuilds derived winning rows from already
projected post-launch facts, respecting a partially processed draw cursor; it does
not replay purchase/day counters a second time or alter immutable business data.
Runtime/profile reads do no replay. The old uncommon adjacency regression now
expects the true length-three result after inserting the late middle winner;
the uncommon award threshold remains two.

Necessary validation: 120 backend achievement/common/uncommon/gift tests passed,
12 targeted frontend tests passed, Mini App lint/typecheck/build, Ruff/mypy and
Alembic check passed. Browser 320/390 px verified all 20 cards, filters, earned
blue badge, full-card Bingo reward detail, numeric 1000 mark and overflow absence.
Evidence and exact files are in docs/achievements/ACHIEVEMENTS_RARE_LOCAL_REPORT.md. Local DB
backups precede the migration. No release or VPS publication for this task.

## [Rare achievements — proposal history] - 2026-10-20

Owner supplied 20 rare achievements and asked for proposed rewards. Prepared
docs/achievements/ACHIEVEMENTS_RARE_PROPOSAL.md and pending OD-072: 300k–750k CAS per entry,
9,650,000 CAS total, 80 gift tickets/cards and ten planned cases. Inspected actual
CODE rules/UI: five equal ordered digits and no separate cipher; proposed exactly
four matching positions of five without changing the lottery. Reused prior owner
confirmation that Bell means Ball. Preserved uncommon activity conditions and
recorded explicit PULSE/repeat-result interpretations for approval. No catalogue,
runtime, DB or payout changes; no tests for this documentation-only proposal.

## [Uncommon achievements and gift packs — implemented locally] - 2026-10-20

Owner approved the revised 23 uncommon entries and all condition interpretations,
confirmed Casper Ball, and added September x3 for calendar flip, Grand x1 for Rich
and PLL x2 for Little by little. Final category totals: 3,575,000 CAS, 50 tickets/cards,
eight planned cases. Added versioned uncommon catalogue, preserved player-facing
flavor copy, shared post-launch counters and mint outline artwork. Original 22
common rewards and immutable award snapshots retain their economic meaning.

Migration 0062 adds sparse indexed daily/paid-winning-draw projections and flavor
copy. Purchase/refund capture persists original Moscow purchase day. New calendar
and neighbouring-completed-draw conditions update on events; only affected result
conditions are checked. Management performs one explicit paged initialization
from already processed post-launch events, including a partially projected draw's
cursor; runtime revision prevents a second replay. API reads do no replay or grant.

Funded gifts now support weekly Grand and standard Bingo pool allocation. Packs
reuse separate immutable one-ticket reward parts, unique ticket origin, ledger
transactions and waiting retries; UI groups them into the actual ticket/card count.
Unfulfilled parts may continue in a later eligible draw without duplicating paid
parts. No case inventory, lottery economic changes or production publication.

Necessary checks and local evidence are recorded in
docs/achievements/ACHIEVEMENTS_UNCOMMON_LOCAL_REPORT.md. The desktop preview has the migrated
database and 45 definitions with its original epoch/player history retained.

## [Uncommon achievements — proposal history, local] - 2026-10-20

Owner supplied 23 uncommon achievements and requested rewards before local
implementation. Prepared docs/achievements/ACHIEVEMENTS_UNCOMMON_PROPOSAL.md and pending OD-071:
2,925,000 CAS across 23 entries, eight optional daily-draw tickets, four optional
planned cases. Inspected existing conditions/results/rules: Bingo already stores
row closing moves with the 18-move first-tour cutoff; Casper Bell was not found,
whereas Casper Ball supports 2+0. Presented that naming question and precise
PULSE/Grand, consecutive-draw, day-boundary and participation-group interpretations
for owner approval. No runtime/catalog/DB changes, reward assignment or publication;
tests were not run for this documentation-only proposal.

Owner subsequently raised the uncommon range to 100k–300k CAS and ticket packs
to 3–5, requested additional cases and Grand/Bingo/matching 6/36 tickets.
Revised the proposed allocation to 3,575,000 CAS, 44 tickets/cards and eight planned
cases. Inspected delivery constraints: retain one ticket per idempotent reward
part and group them for display; Grand needs weekly eligibility, Bingo standard
pool selection. Those adapter changes have not yet been implemented. Updated
OD-071 and the proposal only; common rewards stay intact and no tests were run.

## [Approved achievement icons and rarity colors — local only] - 2026-10-20

Owner approved direction 1, "Контур с характером", and delegated rarity colors.
Applied the 22 approved outline glyphs, small marks and selected asymmetric tiles
through a shared AchievementBadge in profile, catalogue, details and notices.
An ID-based presentation mapping updates old award artwork without mutating
immutable award snapshots, catalogue conditions, rewards, player data or schema.

Centralized common silver-lilac, uncommon mint, rare blue, epic violet and
legendary gold. Locked icons are muted; locked secrets reveal only a lock and no
threshold/shape hints. Earned secrets retain their actual rarity. Embedded only
26 selected static Lucide 1.17.0 glyphs with ISC/MIT notices; no external icon
request, full icon library, polling or backend computation was introduced.

Validation: Mini App lint/typecheck/build and all 197 frontend tests pass, including
three focused badge regressions. One initial parallel-suite navigation timeout
passed in isolation and on the complete rerun with two workers. Browser smoke at
320/390 px covered profile, all 22 glyphs, pagination, details open/close and no
horizontal overflow; checked all five colors using temporary DOM-only samples.
No browser errors; Telegram's existing browser-mode haptics warning remains.
Evidence and files are in docs/achievements/ACHIEVEMENT_ICONS_LOCAL_REPORT.md. Changes remain
local per owner instruction; no release or VPS operation for this icon work.

## [Owner digest delivery and distribution visibility] - 2026-10-20

Read-only production audit identified API/bot owner-recipient configuration drift:
both 18/19 October digests were cancelled as owner_report_recipient_changed.
Forward OWNER_TELEGRAM_ID to both services. The application service can requeue
only the currently due, definitively unsent cancelled report with that exact
reason, same active owner and a row lock. SENT/UNCERTAIN/expired reports stay intact.

Pulse #7276, 20 October 03:42 MSK: recomputed all 120 purchased combinations with
the saved rules and verified every prize and distribution share against the
immutable player ledger. No discrepancies. Four 2+0/cipher-no tickets each received
10,054,000 distribution + 14,000 ordinary = 10,068,000 CAS. Distributed pool:
40,216,000; ordinary prizes: 204,000; all prizes: 40,420,000 CAS.
Admin decoded cipher match codes below 100 as legacy two-field codes: code 20
incorrectly appeared as 2+0 instead of 0+2. Decode with the recorded ruleset.

Expose existing distribution metadata through admin DTO/API, completed history
filter and paginated draw lists. Show bounded last-50 history in designation view,
with links to immutable results and explicit roll-down summary/recipient labels.
Remove retired channel-post confirmation copy. No draw/ticket/ledger/schema changes.
Release is isolated from the owner's unshipped local achievement work.

Validation and production completion are recorded in docs/OWNER_DISTRIBUTION_AUDIT_2026-10-20.md.

## [Laptop preview launcher — local only] - 2026-10-19

Owner requested a desktop shortcut for the latest local version. Added a Windows
launcher with loopback-only API/Vite/PostgreSQL, a persistent dedicated sandbox,
automatic Docker readiness, single-instance locking and process-tree cleanup on
console closure. The sandbox uses approved current lottery terms on initial empty
database setup, ledgered fund movements, the 22-entry achievement catalog and the
existing browser development authentication. No historical economy transition is
replayed. Subsequent starts retain tickets, balances, awards and launch timestamp.

Python children use a separate working directory and an allowlisted environment;
the production .env, bot credentials and VPS credentials are not loaded. Bot,
editorial, owner summary and Telegram achievement delivery stay off. Created the
explicitly requested desktop shortcut; instructions are in docs/LOCAL_PREVIEW.md.
No VPS connection or publication.

Validation: full backend suite 793 passed / 1 Windows symlink skip, plus all three
focused launcher tests after the Windows lock regression check was added. Ruff
and diff whitespace checks pass. Real local HTTP/browser smoke covered profile,
22 definitions, a paid instant purchase and four resulting achievements, hard
supervisor termination with API/Vite cleanup, restart through the actual desktop
shortcut, retained progress and single-instance reuse. The preview remains open
for the owner; local test data is intentionally retained.

## [Common achievements and profile — local only] - 2026-10-19

Implemented the owner's 22 common achievement definitions without assigning reward
amounts. Confirmed custom games are september/pll/grob; owner explicitly reiterated
local-only work. Added pending reward configuration, paid-price payout comparisons,
immutable ticket selection provenance and purchase operation UUID, manual/bulk/
successful reward metrics, post-launch paid result filtering and instant-game
distinct counts. Refund corrections preserve purchase milestones consistently
regardless of worker delay; ledger and lottery economic rules are unchanged.

Added bounded summary/filter/pagination reads and indexed unread award notices.
Compact profile balance, summary with the actual latest three, one rarity at a
time, progressive list loading, native accessible details, matching SVG icons and
sequential notices. Pagination refreshes if progress or catalog revision changes;
there is no achievement polling loop or source-history scan on a screen open.
Manual origin is reset after each confirmed purchase, including repeated CODE
entries. Retired channel publications/stories remain retired.

Prepared an isolated local database k_loto_achievement_common_20261019 with exactly
22 definitions and zero users/awards. Amounts/funding/production launch still need
owner approval (OD-066/OD-068). Full details and verification evidence are in
docs/achievements/ACHIEVEMENTS_COMMON_LOCAL_REPORT.md. No production deployment or connection.

Validation: backend 791 passed / 1 Windows symlink skip, Mini App 191 passed,
Admin 66 passed, both client lint/typecheck/builds, Ruff and mypy (102 files).
Local Alembic upgrade/check matched the ORM. Browser QA covered narrow screens,
larger text, billion-CAS balance, dialog focus, filtering/pagination and the
lightweight toast fade. Source backup with SHA-256 manifest saved under .tools.

## [Editorial retirement and server optimization] - 2026-10-19

Owner explicitly approved off-host archiving followed by irreversible removal of
channel publications and related Mini App stories/feed. Production editorial work
is disabled by default and in both compose backend services. Scheduler and queue
entry points return before SQL; publication routes return 410; stories and admin
editorial navigation removed. Distribution assignment and money/draw logic remain
available without channel announcements. Assets excluded from clean client builds,
release inventories and backend images.

Off-host exports and SHA-256 receipts precede deletion. The explicit maintenance
operation truncates only five editorial tables and deletes only PUBLICATION audit
rows with the immutable-audit trigger restored in the same locked transaction.
Counts of tickets, draws, ledger and non-editorial audit must match. Financial
guards remain active. Cleanup stays in server_maintenance.py and exact archived
paths/images are used; no broad Docker pruning or volume removal.

Release work is isolated from the unshipped achievement foundation; migration 0059
and achievement API/worker/client changes must not enter this publication.
Validation and production measurements: docs/EDITORIAL_RETIREMENT_2026-10-19.md.

Production completion: all editorial tables/audit empty; old publication assets,
archives, seven historical app images and two exact BuildKit cache records removed
after verified off-host copies. API/bot/gateway healthy; editorial API returns 410.
CPU in two 41.3s windows: 17.14% / 18.30% (previously 81–82%);
publication scan deltas zero. Disk now 40% used, about 24.3 GB available.
Live schema stays 0058; achievement tables absent. Fixed pg_dump nonce comparison
and verified stable schema hashes. Full evidence and validation limits in report.

## [Read-only VPS capacity audit] - 2026-10-18

- Owner requests an approximate audience/capacity assessment and upgrade signals. Read-only SSH inventory, two short passive observation windows and eight bounded sequential application-service reads; no deployment, production settings/history/money changes, notifications, test users/purchases or saturation load. Own probe connections enforce read-only transactions and short timeouts. Added docs/CAPACITY_AUDIT_2026-10-18.md and private local aggregate artifacts.
- Host has one vCPU, 1.76 GiB usable RAM, approximately 40 GB storage, and shares resources with VPN containers. First 42.3-second window averages 82.42% CPU across samples (50–100%); PostgreSQL averages 57.26% and API 10.04% of one core. A second 23.1-second window again shows high CPU. Available memory remains roughly 764–795 MiB with no swap-out during either observation; disk 56% used. Health checks succeed and the observed scheduler heartbeat has no current error. These are short windows, not daily percentiles or verified audience limits.
- Active SQL repeatedly comes from publication expiration/queue checks. During the second window publications adds 31 sequential scans / 538,594 scanned rows, no added index scans, over approximately 17,374 publication rows. Existing two-second background dispatch performs these checks; the report records the exact optimization target without modifying it. Achievement foundation remains local/inactive and is not the source of this production observation.
- No claim that 1,000/5,000/10,000 concurrent users are supported. Distinguish registrations from simultaneous activity and show the current two-second live-snapshot demand calculation. Recommend addressing background query work before final sizing, a separate 4-vCPU/8-GB candidate as planning headroom (not a tested capacity promise), and sustained CPU/latency/memory/disk/lag triggers rather than a registration-count cutoff. Full product checks/release are inapplicable to this diagnostic/document-only task; remote read-only guards, artifact validation and final health checks cover the actual scope.

## [Local foundation — achievements, OD-066] - 2026-10-18

- Owner explicitly authorizes a concrete specification and local implementation, delegates technical choices and prohibits production publication/activation and a real catalog. Added docs/achievements/ACHIEVEMENTS_SPEC.md, the local delivery/operations report and a generated JSON catalog schema. Preserve the completed economy transition and existing unrelated worktree material.
- Migration 0059 adds a disabled singleton, sparse per-player metrics, unique draw participation, a transactionally captured PostgreSQL queue, immutable award/reward snapshots and refund corrections. Capture coalesces ticket/ledger facts over the entire transaction even with SQLAlchemy executemany. A completed nonempty draw creates one resumable marker, not one event per ticket; indexed pages hold at most 100 results. No payout rules, source business history or real balances are changed.
- A revision-cached catalog indexes changed metrics and lottery filters; one-time acquisition, ledgered CAS reward parts and balance/meta cascades are retry-safe and run in separate background transactions. A processor-only advisory lock, short SQL/lock timeouts, per-player ordering, bounded tick work and eight-attempt quarantine keep failures isolated. Reintroduced/new filters rebuild only already processed post-launch facts in an explicit local management operation. No prelaunch history backfill.
- Added authenticated catalog/progress/preferences/featured/activity APIs. Secret locked entries omit identifying content/conditions/rewards. Period checks reuse loaded award timestamps with binary search. Mini App records opening independently of first-screen rendering; no page design or polling. Existing inbox/outbox and conservative Telegram UNCERTAIN policy are reused, with separate opt-in and a disabled transport switch. Gift/cosmetic adapters cannot activate before implementation; trusted source/metric/reward registries support later cases/inventory work.
- Required local backend suite: 752 passed / one Windows symlink skip (Linux-only check remains unavailable locally), including 53 achievement tests and ten disposable PostgreSQL scenarios. Ruff lint/format and mypy (101 modules) pass; Alembic schema comparison reports no pending operations. The complete empty-database bootstrap also passes with collection disabled and no definitions/events/awards. Clean npm-ci/typecheck/lint/test/build pass: Mini App 183 tests, Admin 66 tests, both source/artifact manifests verified. A private source-only local ZIP/hash/manifest excludes secrets; the task's local PostgreSQL container is stopped and test scenario databases are removed. No product version/CHANGELOG release is published because the catalog and feature remain off.
- Separate Windows/Docker load sample: 500 fixture definitions, 10,000 results, one draw marker, 500 awards, complete drain in 25.76 s while 50 balance reads continued (read p95 64.23 ms). Existing purchase service retains two queue rows for 1,000 tickets. Three disabled samples: 3023.35/1527.38/1296.60 ms; enabled: 1602.36/1534.69/1271.21 ms. Cold/short local samples are not production latency, p95 purchase capacity or a VPS guarantee. Final catalog, real CAS funding, notification copy/UI and explicit production launch remain later decisions; no release/deploy, real Telegram send or reward occurs in this task.

## [API 1.57.0 / Mini App 1.67.0 / Admin 1.61.0 — combined economy release] - 2026-10-18

- Owner explicitly ends the local accumulation window and authorizes full checks, backup, publication and reopening. Consolidates OD-057 through OD-064: Vault/LIVE, Fast, thematic games, Classic/Ball/Grand, Dual/Bingo, Admin simplification and the private daily owner digest. No collection, leaderboard or case implementation is included.
- Initial production pause already completed 5,755 full ticket refunds (114,696,080 CAS) and cancelled 159 future draws. Do not repeat it. Preserve completed history, purchased/refunded tickets, counters and epoch 2. Apply the four remaining idempotent batches with compensating jackpot/Fund ledger entries and audit; do not invent new bot balances or issue extra Fund money.
- New payout versions preserve historical settlement. Exact integer per-ticket shares include upward half-share rounding for September. Dual validates the fixed maximum at transaction completion in migration 0058; Bingo keeps 58 moves, stacks fixed per-card prizes, preserves jackpot sharing and removes only unsold pool rows transactionally after settlement. Generation is unchanged.
- Admin defaults to the current epoch, keeps the old economy archive, loads technical views on entry and exposes complete-operation daily CAS flows. Owner digest uses the same report, Moscow calendar days, observed Fund depletion and the existing private outbox with deduplication. Production recipient is configured and matches an active user; no channel announcement is sent by this release.
- Local full backend suite: 709 passed; one Windows symlink check deferred to Linux candidate validation. Ruff lint/format and mypy (95 source files) passed. Clean frontend and production/disposable PostgreSQL verification results are recorded below when complete. Production remains paused until all required checks and economic batch verification succeed; reopening records an explicit recovery checkpoint instead of replaying maintenance slots.
- Clean npm-ci/typecheck/lint/test/build passed for both clients: Mini App 182 tests, Admin 66 tests, source/artifact manifests verified. Corrected an obsolete Vault test fixture that funded three tickets at the former price; runtime correctly rejected the underfunded purchase. Built-client Chromium smoke passed: Admin overview/economy at 1440/390 px, no eager diagnostic requests, no JS errors or horizontal overflow; Mini App maintenance-to-open/auth-entry transition passed. Mobile layout visually inspected.
- First Linux candidate passed 85 tests (including the Windows-skipped symlink case), runtime lock and migration checks. Financial smoke correctly failed closed because a schema-only clone omitted migration-seeded `economy_control`. Restore its default singleton in the guarded disposable financial fixture with INSERT ON CONFLICT DO NOTHING; never override an existing pause or change the production guard. Candidate failure occurred before promotion, production migration or worker recreation.
- Updated the real PostgreSQL Bingo ledger assertion to include the approved 30,000 CAS burn for each purchased card; the old zero-sum expectation predated the 40/60 split. Fixed ordinary prizes and jackpot transfers remain balanced. The HTTP smoke now expects four Bingo summary categories for the new fixture instead of the historical three. These are test-fixture corrections, not changes to the approved economics.


- Published runtime commit `c137fca` (API 1.57.0 / Mini App 1.67.0 / Admin 1.61.0), migrated production to 0058, and verified all three services under the operations lock. Database/source backups and pre-recreation diagnostic log archives completed; 85 Linux candidate tests, runtime lock, migration/autogenerate checks, financial/delivery/HTTP/profile regressions, empty-schema bootstrap/index recovery, public client hashes and authentication boundaries passed. The expected deliberately failing recovery fixture remained isolated to the disposable database.
- Restored the real pre-release backup into a disposable database: 12 users, 22,036 draws, 724,837 tickets and 364,872 ledger rows; all five account families reconcile and indexes validate. A separate PostgreSQL pause/refund/archive/resume regression passed. A full production clone passed all four approved batches, repeat application without new ledger entries, exact rules/base/limit checks, unchanged historical row/wallet/counter hashes, zero current-era game/CAS activity, readable old archive and reopening with no maintenance backlog. All owned rehearsal databases were removed.
- Applied the four batches once in production and repeated the same history/account/idempotency/archive checks successfully. Kept the original epoch 2; no repeated refunds, wallet resets or extra Fund issuance. Before reopening, current analytics contained zero tickets/completed/pending draws; archive retained 724,837 tickets and 21,877 completed draws. Enabled the actual Compose setting `K_LOTO_SCHEDULER_ENABLED`, with the maintenance gate still closed during restart.
- Explicitly reopened at **2026-10-18T01:29:27.659387Z (04:29 Moscow)**, recording the same recovery checkpoint. Public Mini App/Admin checks and independent monitoring passed with no warnings. Telegram getMe verified `Kasper_loto_bot`; authenticated current/archive overview, economy, ticket analytics and jackpots returned successfully. Scheduler heartbeat advanced beyond reopening with no error; all eleven scheduled games have upcoming draws and no non-cancelled draw falls inside the maintenance interval. Existing bot auto-play resumed: the new epoch already records fresh purchases, separate from the unchanged old archive. The private daily summary is enabled for the configured active owner, from 00:05 Moscow after the report day; no manual channel announcement was sent.
- Prepared `archive/reference/retired-publications/docs/publications/economy-update-2026-10-18.md` for the owner's player announcement. Normal release rules are restored in AGENTS.md. Final evidence/text-only source publication does not rebuild or restart the running services. Unrelated OD-054 worktree changes and design files are preserved.

## [Planning — Production economy baseline and proposals] - 2026-10-17

- Owner requests a full current lottery price/jackpot/prize/limit inventory and recommendations before economy implementation. Read production in an explicit repeatable-read/read-only transaction; inspect deployed public rule/service source. Export only configuration, pool balances, rule tables and source digests, with no personal records or credentials. Snapshot 2026-10-17T19:59:49.641470Z covers eleven active scheduled and three instant games; archived daily is identified separately.
- Added a Russian review, sanitized source snapshot and standard-library exact-fraction recalculation. Separate shared-pool no-sharing references from fixed instant/Dual payout expectation. Highlight Vault 446%, easy-game full-coverage capacity, absent daily cap, real five-second purchase limiter window, welcome-grant scale, reserve funding/distribution effects and Ball's missing lower ball-match tiers. Mark the September lottery reference stale.
- Provide an explicitly unapproved linked price/base/category/cap model and implementation order, recorded in OD-056. No settings, domain rules, schema, balances, tickets, scheduled/completed draws or production services are changed. This is documentation/analysis, with no application release/deployment. Preserve unrelated OD-054 and design worktree changes. Validation: exact probability sums, fourteen-game coverage, coverage costs and expected payouts; reproducible calculations and document/source cross-checks.

## [Planning and channel artwork — October roadmap] - 2026-10-17

- Owner confirms the six October roadmap directions and requests a Telegram-ready image and a separate implementation order. Replaces the earlier no-repeat-only case proposal with a seasonal mixed-reward case: collectible figures, lottery tickets and virtual CAS, with weighted chances and a roughly three-month cadence. “50/12” is an example; precise rules remain open in OD-055.
- Created the 1086×1448 PNG `assets/roadmaps/2026-10/roadmap-october-2026.png`, optional caption and generation provenance. Used built-in ImageGen and a targeted correction removing unintended ghosts/crown; final typography and all six texts visually checked. Public copy contains no unapproved counts, prices, probabilities or exact release dates. The owner will post it manually.
- Added `docs/OCTOBER_2026_IMPLEMENTATION_ORDER.md`: economy modelling, shared reward/inventory accounting, leaderboard/public profiles, badges/achievements, seasonal collection/case, tasks/bonuses, and a ledgered test-balance transition after replacement grants work. Notes ticket-funding and payout-return effects. Updates the earlier draft and illustrative case copy to reflect mixed rewards.
- Planning/media only: no business-rule/schema/runtime/production change or balance adjustment. Basic image integrity and focused prototype checks verify delivery assets; application release checks do not apply to this asset-only task. Existing unrelated OD-054 worktree changes are preserved.

## [Planning — Collections and public showcase] - 2026-10-17

- Owner discusses a fifth leaderboard destination, collections, cases for virtual CAS and a gold badge for a genuine “6 из 36” jackpot; confirms current accounts are owner-controlled test bots. No financial adjustments are performed.
- Added an illustrative clickable navigation flow and a draft roadmap: keep collection/case entry inside “Моё”, show selected items/badges on a public masked player card reached from the leaderboard, and distinguish event-earned badges from purchasable collection items. Case price, item count/content, no-duplicate policy and gift case are explicitly unapproved examples/proposals, tracked in OD-055.
- Planning artifacts only; no application/business-rule/schema/production change. Preserve existing unrelated worktree edits, including the earlier OD-054 discussion.
- Fragment validation and JavaScript syntax pass. Focused Chromium smoke covers case result, inventory progress, equipping, own/other public cards, masked names and badge navigation; no horizontal overflow at 780/360/320 px. Symbols are illustrative placeholders, not approved collection artwork.

## [Marketing — Casper free-play Reel] - 2026-10-17

- Owner commissions an Instagram Reel with a hook, animated typography and an explicit free-play message. Added the isolated Remotion project `design/reels/casper-free-v1`, six editable scenes and a Russian post caption. Approved Casper logo/artwork are reused unchanged. Actual Mini App screens are captured from its existing local design preview; demo labels are visible and no real purchases or production records are involved.
- Delivered a 24-second 1080×1920 / 30 fps H.264/AAC video and cover. Original synthesized music/effects are synchronized to cuts and number selections. Claims follow the owner brief and existing virtual-CAS scope: free, no investment, no purchase or cash-out for real money; no cash-prize or guaranteed-win claims.
- ESLint, TypeScript and Remotion bundle pass. All six scene layouts visually reviewed. Final MP4: 720 frames, limited-range YUV 4:2:0 / BT.709, fast-start, full decode passes, stereo 48 kHz AAC, no clipped samples; measured −15.48 LUFS / −1.98 dBTP. Reproducible media checks and output report included. Source and delivery artifacts backed up in the repository's ignored backups directory.
- Standalone marketing deliverable only: no application/service/schema/config changes and no application release or VPS restart. Instagram publication remains the owner's action. Existing unrelated worktree changes are preserved.

## [API 1.56.7] - 2026-10-17

- Owner requests fixing recurring false publication-delay alerts. Incident evidence matches the 12:22/18:35 Moscow scans and legitimate 30-minute sequential delivery, with no failed sends or overdue draws. Preserve that publication policy.
- Record the actual queue-entry UTC timestamp in new automatic/historical snapshots and manual event approvals, independently of the original event time. Preparation/retry does not refresh this timestamp. Existing published content/history is untouched; legacy unmarked drafts retain updated_at as a fallback. No schema migration.
- Delivery and monitoring use the existing DeliveryPolicy. Health checks only the eligible queue head after its permitted slot plus the configured ten-minute grace; Telegram retry_after is respected. Unresolved sends are reported as blockers, paused transport is not an overdue queue, and real failed/uncertain sends remain actionable. Archived/published/ineligible/stale-series rows cannot generate a queue delay.
- Full backend suite: 624 passed / one Windows symlink skip; subsequent manual approval/queue timestamp regression passes with all 20 publication service tests (625 unique backend tests in total). Ruff lint/format and mypy 85 modules pass. Frontends are unchanged. Add the affected unit regressions and a real PostgreSQL queue regression to the release candidate checks. Focused preflight passed in a fresh disposable schema with rollback and verified database cleanup; no Telegram I/O or production business-row changes. Verification/release results follow below.

- Published e0393d4, API only, verified 2026-10-17T16:54:34Z: database/source backups and diagnostic log archival completed under the operations lock; 83 affected Linux candidate tests, the new PostgreSQL monitoring regression, runtime lock, financial/delivery/Mini App/profile HTTP checks and empty-schema recovery passed. No schema changes; bot, database and gateway were not recreated. Public Mini App/Admin/auth/retired-Web checks pass; independent watchdog warnings empty. No production test posts/purchases or historical-data corrections.

## [API 1.56.6 / Admin 1.60.4] - 2026-10-16

- Owner requests a smaller, rarely used Admin. Remove Broadcast test and Interesting facts UI, route old bookmarks safely, consolidate LIVE/Aurora/Vault under Instant games with on-demand game selection, and move Archive to the final navigation position. Keep Schedule as its inexpensive read-only/on-entry view.
- Remove remaining Admin API polling from health, publication proposals and distribution delivery status. Refresh on entry or explicit actions; preserve local clocks for expiry/closed-sales display. Keep publication editing under its own refresh controls so the common refresh cannot discard an unsaved draft. System tabs load only relevant data; loading identity prevents premature child mounts and duplicate initial requests. Ignore obsolete section/game responses.
- Retire the independent legacy Interesting facts startup/daily scheduler job while retaining all existing records and read APIs. Publication suggestions/automation are independent and continue; do not stop draw recovery, delivery, backups or owner alerts when Admin is closed. No business-rule or schema changes. Publish API and gateway only; Mini App and retired Web sources are unchanged.
- Local checks: 607 backend tests passed (one Windows symlink skip; Linux candidate covers it), Ruff lint/format and mypy 84 modules pass. Clean Admin npm ci/typecheck/lint, all 56 tests, production build and artifact hashes pass; unchanged Mini App artifact hashes verify. Regressions cover on-demand game summaries, late-response fencing, legacy bookmarks, scoped system-tab loading, five-minute idle health and manual proposal refresh. Chromium smoke against built static files uses only mock API data: all three game tabs request exactly one summary each, no requests in five simulated idle minutes, no console errors and no horizontal overflow at 390 px. Production results follow below.

- Published 9bb80f9: API 1.56.6 / Admin 1.60.4. Backup, verified delta upload, candidate runtime/PostgreSQL/HTTP checks, Caddy validation and public client/auth/retired-Web checks pass. Only API and gateway recreated; no schema change or production test purchase/post. Final verification 2026-10-16T19:25:07Z: legacy fact job absent in active API source, backup/maintenance timers active, independent watchdog warnings empty.

## [API 1.56.5 / Admin 1.60.3] - 2026-10-16

- Owner authorizes reducing Mini App SSE and Admin read load and verifying bounded production retention. The shared public live snapshot is an immutable worker/engine-local single-flight cache (two seconds, 32 keys, scope/lottery separation). Personal results stay outside the cache: one grouped owner-only aggregate plus one window-ranked query for all recent draws; Dual includes second-round links. Khan reveal selects one best partial-match ticket in SQL instead of hydrating every owned ticket. Display caches never authorize sales or change settlement.
- Admin draw details initially fetch metadata and SQL aggregates without hydrating tickets. Owner requests subsequent 50-ticket pages by public-number seek cursor and all/winners/jackpot filters. Counts and Bingo stage summaries cover the whole draw independently of loaded pages. Jackpot flags use one filtered ledger join rather than a full correlated scan for every ticket.
- CAS history remains owner-requested batches of 100, now seeking by UTC created_at plus UUID for stable timestamp ties. UI serializes page requests and ignores obsolete filter responses. Dashboard/Fast full-history polling every 30 seconds is removed; data refresh on opening and the existing refresh button. Number statistics load only on their own tab; all ticket-analytics scopes receive the same bounded single-flight one-minute display cache.
- Baseline read-only production measurement on two existing players: 12 recent live cards, 27 SQL statements for each request (199.2 / 69.8 ms). Small sequential service sample, not phone/HTTP p95. Production comparison and retention cleanup verification are recorded after release. No schema/money-rule changes; publish only API and gateway. Standalone Web remains excluded.

- Local validation: backend 607 passed / one Windows symlink skip; Ruff and mypy 84 modules pass. Clean Admin typecheck/lint/53 tests/build and source/artifact hashes pass. Unchanged Mini App build hashes verify. Candidate HTTP/PostgreSQL checks now include complete seek traversal of draw tickets and ledger timestamp ties, summary-only draw/Bingo requests, invalid bounds/cursors and live owner/outsider isolation.

- Release preflight exposed a pre-existing 8 KB diagnostic-tail truncation in the structured gateway chunk inventory. Capture that inventory separately up to an explicit 1 MB bound, reject incomplete digests, and avoid printing the full list. Add regressions for output over 8 KB, all inventory entries and truncated digest rejection. The first publication attempt stopped before source promotion/container replacement.

- Published API/gateway after 65 Linux candidate tests, runtime lock verification, financial/delivery/real HTTP checks and fresh-schema recovery; source snapshot 7,220 files, only 25 transferred (612,398 bytes). Public exact clients, authentication boundaries, retired Web and independent monitoring pass. Follow-up Admin empty-filter wording and loaded-count clarification passes lint, a focused pagination/filter test and a fresh clean typecheck/build; published with gateway only. Final backend suite: 607 passed / one Windows symlink skip (Linux candidate covers it); Admin 53 tests and 22 affected Mini App live tests pass. API 1.56.5 / Admin 1.60.3; no schema change, bot not recreated.
- Read-only production comparison on the same existing player, four sequential calls per version using the retained bot image (1.56.4) and API image (1.56.5): old SQL counts 27/27/27/27, new 4/2/2/2. After the first call, old service wall time 173.1–247.9 ms (SQL execution 92.2–111.5 ms), new 32.0–41.7 ms (SQL 11.9–12.9 ms). First calls 773.5 / 257.9 ms respectively. Public draw queries run twice on the first new request and zero times on a subsequent cache hit. Small warm service sample, not HTTP/phone latency, p95 or a capacity test. No production test purchase or channel message.
- Retention applied at 2026-10-16T18:12:15.800691+00:00: 7 database dumps retained; 5 old owned archives/uploads and 4 eligible project images removed, 1,694,846,976 bytes reclaimed. Post-cleanup plan: 0 surplus recognized files, 0 eligible images. Removed file paths verified absent; health passed. Daily maintenance remains active; dump retention is seven copies, source rollback retention three per recognized category. Business history is permanent.

## [Operations] - 2026-10-16

- Owner authorizes backup repair and owner notifications following the outage audit. Replace the broken direct cron execution (permission denied, exit 126) with a versioned native systemd service using explicit shell execution, the operations/backup locks, and a persistent 03:30 Europe/Moscow timer. No application container recreation or schema changes.
- Independent host monitoring checks real nonempty backup freshness and the backup service result, forwards only independent runtime warnings, and sends private incident/recovery alerts through the existing owner bot. Atomic private delivery claims suppress duplicate ambiguous sends; definitive rejections retry with delay. Full-host downtime and same-VPS storage remain explicit limitations.
- Restore checks use a unique disposable database, clean up only databases they created, and validate the restored schema, five ledger/account families and indexes. Final backend suite: 598 passed, one Windows symlink skip; 13 focused notification/freshness regressions and Ruff pass. Linux file-selection checks cover symlink/hardlink/partial exclusion separately on the VPS.
- Published host scripts/units under the operations lock after fresh database and private source/configuration backups. The exact systemd job finished with Result=success / ExecMainStatus=0; Persistent=yes, next run 2026-10-17 03:30 MSK. Removed only the verified obsolete backup cron entry and verified timer/health activation; API/bot/gateway were not recreated. Explicit private owner configuration matches the active API owner and bot token.
- Fully restored k-loto-20261016T170612Z.dump (82,807,696 bytes) into a unique disposable database: 12 users, 21,432 draws, 697,652 tickets, 342,355 ledger rows, schema 0056_player_profile_projection. All five account/ledger checks and index validity pass; disposable database cleanup confirmed. Seven retained dumps; public Mini App/Admin HTTPS and retired Web checks pass. Watchdog warnings empty at 17:08:37 UTC; owner setup notification confirmed by Telegram. Backup copies remain on the VPS under the previously approved server-only policy; no external uptime monitor was configured.

## [API 1.56.4 / Mini App 1.66.5] - 2026-10-14

- Owner authorizes Mini App profile performance work, selects the last 1,000 tickets for favorite numbers and defers any explanatory UI copy. Keep favorite lottery lifetime semantics; select the last 1,000 eligible tickets of that lottery, exclude refunds and instant games without chosen numbers. Admin minimization is outside this release.
- Migration 0056 creates rebuildable per-player totals and per-player/lottery counts, backfills existing history and maintains them through statement-level PostgreSQL transition-table triggers in each source write transaction. Cover regular insertion/settlement/refund, immutable instant insertions and non-result unread notifications. Group by player rather than applying a whole-history query or an update per ticket during bulk writes. Money and draw rules remain in application services; projection triggers never move CAS or modify source history. New users receive an empty summary in their insert transaction.
- Profile reads current balance plus all totals in one query, favorite lottery from bounded per-lottery counters, and numbers from an indexed last-1,000 subquery before unnest/group/limit. Stable timestamp/UUID ordering, deterministic frequency ties, refunded exclusions. No unbounded fallback on reads. Derived-data rebuild locks source writes and requires READ COMMITTED; independent verification compares all summaries to source history in one SQL snapshot. scripts/check_player_profiles.py is read-only by default; --rebuild explicitly reconstructs derived data only.
- Mini App requests 20 tickets per page. A 30-second in-memory navigation cache is scoped to Telegram identity and snapshot epoch, coalesces same-epoch navigation requests, rejects late responses and retains explicit refresh after mutations. No profile copy or layout changes; existing on-demand detail/history behavior remains.
- Validation: backend 577 passed / one Windows symlink skip (covered by Linux candidate); Ruff and mypy 84 modules pass. Clean Mini App typecheck/lint/175 tests/build pass; final navigation/force-refresh refinement passes all 41 App tests and a fresh clean build. Admin typecheck/lint pass; its full suite had 48 passes and one Escape-close timeout under concurrent checks, with both jackpot-detail cases passing when repeated alone. Unchanged Admin clean build passes. The candidate verifies 49 locked distributions and passes 62 Linux tests, financial and real Mini App HTTP scenarios, projection source consistency/replay/rollback/concurrent writes/refund/unread/rebuild/recent-window/index checks, plus empty PostgreSQL bootstrap/index recovery through 0056 and alembic check. No Web build/check/publication.

- Published fc33a1c under the operations lock: DB/source backup, retained rollback images, archived API/bot diagnostics, migrated 0056 and restarted API/bot/gateway. Verified 7,244 snapshot files; transferred only 37 changed files (661,962 bytes). Public HTTPS, exact clients, auth boundary and Web retirement pass; 14:22:35 UTC watchdog warnings empty, API healthy. All five ledger/account discrepancy counts are zero, all profile and per-lottery projection mismatch counts are zero, no disposable databases/candidate directories remain. No production test purchase or Telegram test send.
- Sequential post-publication read-only measurement on the largest account (129,096 regular tickets): complete account service 339.8 / 32.1 / 38.3 ms, three SQL statements per call. Before this release the same measurement path took 2,722.7 ms. The selected window contains exactly 1,000 eligible tickets; independent Python frequency counting matches the returned numbers; installed profile source SHA-256 matches local. Small first/warm-call sample, not HTTP/phone latency or p95. Full-history totals are now projected rather than recomputed per profile read.

## [API 1.56.3 / Mini App 1.66.4] - 2026-10-14

- Owner authorizes audit step 5 for Mini App runtime only: clean builds, release correctness, integration and large history. Admin remains active; standalone Web remains locally retained and excluded from production source/build inputs. Separate stage 2 authorization/execution is absent; the consolidated report explicitly preserves the remaining Admin-auth, inactive-player, session, no-op-command and rate-limit findings.
- History uses deterministic mixed-source seek pagination, page-sized ORM hydration and complete draw-group counts. Cursor validates owner/filter/time/types; Mini App serializes next-page clicks and fences stale filtered responses while keeping the current list visible. Profile favorites use SQL unnest/group/order/limit instead of Python over every combination. Preserve old offset transport and read-only business rows. Invalid favorite domain input now maps to HTTP 422.
- Runtime install uses pinned uv with locked production dependencies and exact setuptools. Correct existing lock omission of Pillow, verify installed packages and save runtime manifest. Client builder copies only one client plus shared sources into a fresh workspace, npm ci/check/build, verifies source/output hashes and refuses stale --reuse-built. Clean checks exposed a Mini App brand test importing retired Web and Admin; keep each transport regression inside its own client.
- Release stages an exact hash-verified candidate and separate image tags, exercises isolated PostgreSQL + real signed HTTP before promotion, uses the selected new backend image for migrations, preserves untouched gateway artifacts and bounded prior hashed chunks. Hold operations lock through DB/source backup, upload, build, log archive, migration/restart and public health. Persist ownership manifest; retire only unchanged obsolete managed source. Refuse blind old-worker restart after partially changed schema; pending shared migrations require both API and bot. Source archive retention is registered with existing maintenance; no broad pruning or volume cleanup.
- Empty-schema migration entry point seeds only zero historical prerequisites after refusing existing business history, then runs approved historical migrations. Existing versioned databases receive ordinary upgrades. Migration 0052 verifies and reuses its valid indexes, recreates its own interrupted invalid index and rejects a conflicting definition. Disposable empty PostgreSQL checks target 0051, reproduce partial/invalid index states, then complete through head and alembic check.
- Validation before candidate: clean locked Windows Python environment, 570 backend tests passed/one Linux symlink skip before adding one source-backup regression; later 34 release/maintenance tests pass/one platform skip. Ruff and mypy (83 modules) pass. Mini App clean typecheck/lint/174 tests/build pass; Admin clean typecheck/lint/49 tests/build pass. The first released Linux candidate passed 48 focused regressions, financial/HTTP scenarios and fresh migrations through 0055; subsequent interrupted API-only publication is resumed below. GitHub workflow added and YAML parsed; no Git remote is configured and Actions has not run.
- Resumed and completed the interrupted API-only candidate on 2026-10-14. Verified the existing image digest, 87 installed backend files, all 49 locked runtime distributions and 24 relevant Linux tests. Under the operations lock, took fresh DB/source backups, preserved diagnostics, drained and replaced API only. Public HTTPS, exact Mini App/Admin assets, auth boundaries and retired Web passed; 13:27 UTC watchdog warnings empty and Docker API healthy. Installed history source matches local; all five account-vs-ledger discrepancy counts are zero; no disposable audit databases or candidate directories remain. No frontend rebuild, money/schema change, production test purchase or Telegram send.
- Profile verification: favorites-only A/B on one read-only snapshot of 128,991 tickets measured SQL aggregation 398/638 ms versus legacy Counter 1,152/1,636 ms, equal top frequencies. Whole-profile trace during parallel ledger scans measured 8,857 ms; sequential whole-profile A/B on one snapshot of 129,011 tickets then measured current 3,084/1,263 ms versus legacy 5,866/1,595 ms, equal other profile fields. No regression established in this small series, so no rollback. Cache/load effects and full-history aggregates remain; no p95 or load capacity claim. Final reports explicitly distinguish completed work from unexecuted stage 2 and remaining performance/auth findings. Three release-note parser tests pass after restoring newest journal entries to the top.

## [API 1.56.2 / Admin 1.60.2] - 2026-10-14

- Owner authorizes audit step 4 for the Mini App runtime: database integrity, Dual configuration, notification/publication delivery and scheduler recovery. Read-only VPS checks confirm Web routes are retired (/web 410, Web API 404), frontend/web is absent from the deployed source and /srv/web is absent from gateway; existing Mini App/Admin HTTPS and watchdog pass. Local Web sources are retained and excluded from transfer.
- Migration 0055 adds immutable InstantTicket/AdminAuditLog triggers, protects purchased ticket id/source/second_draw_id and already recorded Dual round results, and makes (lottery_id, scheduled_at) unique. Existing completed-draw/ledger/ticket guards remain. Dual price/shape and fixed account balance/base are protected by application validation plus SQL guards. Preflight finds zero duplicate slots and zero invalid Dual accounts; no business-history or account correction is performed. Invalid existing state would block migration instead of being silently repaired.
- Private outbox adds UNCERTAIN. Interrupted claims are quarantined rather than reclaimed for sending; attempts fence stale acknowledgements. Only a definitive Telegram 429 schedules a retry using its delay. BadRequest/Forbidden and invalid formatting cancel safely; unknown errors hold uncertainty. A 60-second network timeout is shorter than the five-minute interruption window. Claims recheck active player, consent, reminder preference and retired message types. Legacy FAILED rows are conservatively quarantined on upgrade; production preflight has none. Only error class/codes are logged, never transport exception text. Admin counts/translates uncertainty as attention required. Recent instant tickets now count as activity for reminders.
- Publication delivery ignores archived blockers, quarantines interrupted sending after five minutes and stops retrying preparation errors. Existing archive action records cancellation/previous state in immutable audit; active sends cannot be archived, stale sends can be resolved even with transport disabled. No uncertain message is resent and no transport is enabled by this change. Distribution and editorial drains run independently.
- Recovery excludes a failed lottery for the rest of the invocation, processes other lotteries and retains chronological ordering inside each. Next cycle retries the failed one. Partial progress is retained in heartbeat counts, but partial recovery does not write success or run auto-play/reminders. Initial recovery failure installs retry jobs and allows API/admin startup; bootstrap schedule preparation also defers failure to runtime. Production bot explicitly has WEB_ENABLED=false and its retired command opens Mini App instead of issuing a code.
- Verification: final full backend suite 563 passed, one Windows symlink skip; mypy 82 modules and scoped Ruff pass. Mini App full suite 172 passed; Admin full suite 47 passed before adding one uncertainty-display regression, then all 35 App tests passed (48 total covered), with final typecheck/lint/build. Actual PostgreSQL schema-only disposable clone passes migration/alembic check, financial settlement/Bingo/Dual replay and ledger regressions, immutable-history/configuration rejection, parallel outbox claims, 429 timing, interrupted/stale delivery and withdrawn consent, failed-lottery isolation/concurrent preparation, instant activity and JSONB publication archive recovery. Fake transports only; no real Telegram test send or production purchase. Linux maintenance tests cover the Windows symlink skip. The initial backend run exposed an outdated test double after introducing lottery-first jackpot locking; the fixture was updated and the full suite passed.
- Late-receipt regression: serialize acknowledgement handling with the same publication advisory lock; a late success/rate-limit/error cannot undo an operator archive. Preserve a successful receipt on the archived row and update the automatic-channel interval from its confirmed acknowledgement; never resurrect/resend the item. Added a PostgreSQL reproduction where the owner archives during delayed delivery.
- Publication: verified source/assets delta, database backup, rollback images and API/bot diagnostic archive under /run/lock/k-loto-operations.lock. Quiesce API/bot before migrating the new persisted enum so old workers never read UNCERTAIN. Build/check candidate before production migration, restart only API/bot/gateway, then verify migration, backup, public clients, retired Web and operational health. Publication completed for fb5f9eb and d77555d: verified all 7,180 source/asset files, uploaded 37 changed files (543,073 bytes) for API/bot/gateway and then five files (162,870 bytes) for the API-only late-receipt correction. Both freshly built candidates passed the isolated PostgreSQL checks, including the archive-during-acknowledgement regression. Applied 0055; validated backups, Caddy, public HTTPS, exact Mini App/Admin assets, auth boundary and retired Web. Final 01:15 UTC watchdog warnings are empty; scheduler error is null, success age 16 seconds, overdue draws 0, balance-vs-ledger mismatches 0, uncertain notifications 0, disposable databases 0. Four new guard triggers are present. Bot WEB_ENABLED=false. Final correction recreated API only; bot/gateway/database stayed running. Temporary transfers/databases removed; rollback images and diagnostic archives retained. No production test purchase or Telegram test send.

## [Mini App 1.66.3 / Admin 1.60.1 / Local Web 1.56.1] - 2026-10-14

- Owner authorized audit step 3 (UI regressions) and requested only necessary tests. Backend financial/auth rules and schema are unaffected; the separate browser client remains retired in production.
- Admin monitoring now requests /monitoring through the existing /api/v1/admin transport prefix. Added a real transport regression instead of relying solely on a mocked monitoring method in the view test.
- Mini App stores shared per-position purchased markers independently of its session-only cart. Purchased IDs cannot reappear after a cloned tab saves stale data, including after a configured display TTL. Keep legacy v1 markers readable. Shared markers carry no combinations, balances or player profile. Coalesce marker storage events into one animation frame and avoid unchanged cart renders.
- Serialize purchase, receipt completion and cancellation with a per-owner Web Lock. Older browsers use a transactional IndexedDB lease; expiry plus the durable pending journal fences a new request while permitting server-idempotent same-key recovery. If neither mechanism is available, fail before sending. Removed the unprotected 40 ms arbitration delay.
- Read shared state inside the lock, preserve a stored receipt when cart cleanup fails, and refuse to let a late old completion/cancellation remove a newer journal. Recovery awaits serialized cleanup and emits one local resolution event.
- Retained local Web: keep the latest balance callback in a ref and use a stable callback in the Khan hook, so parent balance updates do not restart its immediate dashboard fetch. The 30-second polling cadence remains intact. Local-only Web sources/build are excluded from publication.
- Necessary verification: 57 relevant Mini App cart/journal/recovery/App tests, two Admin API/monitoring tests and one Khan polling regression pass. A legacy-marker fixture initially exposed missing sessionStorage isolation in its test file; fixed the fixture and reran that file. After coalescing storage events, reran only its App regression. Affected frontend typecheck/lint and all three builds pass. Real Chromium smoke uses two isolated same-origin tabs with fake receipts and no backend purchases: native Web Locks and actual IndexedDB both block the parallel request and cloned cart; expired lease recovers; unavailable protection never sends. Backend suites and production money tests are not repeated for this frontend-only change.
- Publish gateway only under the operations lock, with a database backup, rollback image and SHA-256 verification of reused source/assets and every changed file. Preserve unchanged graphics and cached hashed chunks; upload the verified delta rather than retransmitting the full asset collection. Verify public HTTPS, exact client HTML/assets, /web retirement and the real monitoring endpoint.
- Publication completed for 865c71a / a6eea59: verified 7,177 source/asset files, uploaded 192 changed files in a 1,125,252-byte archive, validated Caddy and recreated gateway only. API/bot stayed running. Public HTTPS and exact Mini App/Admin HTML and entry assets passed; monitoring returns 401 at its real authenticated endpoint rather than 404; independent watchdog has no warnings. Web retirement remains intact. Synced the release journals to the API for its release-history view. Temporary transfer manifests/archive were removed under the lock; no production purchase was made.

## [API 1.56.1 / Mini App 1.66.2] - 2026-10-14

- Owner authorized stage 1 of the audit (financial correctness/recovery) and retirement of the standalone browser client in production, retaining local sources (OD-052). Prices, odds and completed business history are unchanged.
- Bingo now passes the original client request key into the application service. The guard and cancellation share the original advisory lock, while the service retains historical hashed ledger keys. Receipt lookup finds both ordinary and historical Bingo entries, scoped to their owner. Existing ledger/tickets are never rewritten.
- Draws commit their winning outcome and jackpot obligation before settlement. Retries, concurrent calls and restart reuse that outcome, including missed Bingo and both Dual rounds. Lottery-first locking removes the purchase/settlement inversion; earlier unfinished draws must settle first. Migration 0054 prevents alteration of committed numbers, obligation, configuration and distribution designation. Completed-draw protection remains in place.
- Admin cannot reduce a jackpot below an unfinished draw's committed obligation. Settlement refuses an already underfunded obligation and requires its ledger entries to sum to zero; contributions arriving after outcome preparation remain in the jackpot. No balance is repaired silently.
- Purchase fallback refuses a draw whose sales have already closed; time is refreshed after blocking account locks. Recovery retains missing draws chronologically. Instant purchases require full maximum-prize coverage for the whole batch before calling RNG, under the fund lock; the existing odds and ticket-price burn remain unchanged.
- Production sets WEB_ENABLED=false, excludes frontend/web from Git release archives and both gateway build paths, removes its old server checkout, returns 410 for /web and 404 for its API. Local source/development and existing user/ticket history are retained. Release helper validates Caddy and checks public HTTPS, exact Mini App/Admin HTML, authentication boundaries and retired endpoints under the operations lock.
- Moved the LIVE history ref above the effect that captures it, resolving the existing React lint failure without changing request sequencing. Backend/miniapp patch versions updated; refreshed the root package version in the existing uv lock without dependency changes.
- Pre-release verification: 549 backend tests passed, one Windows symlink skip; mypy 82 modules and Ruff lint on backend/bot/scripts pass; 41 focused financial tests passed after freezing legacy draw configuration. The initial Mini App full run had one lazy-screen timeout (165 passed); repeated with two workers: all 166 passed. Admin 46 and retained local Web 35 tests passed; all three frontend typechecks/lint and production builds pass. Unrelated existing formatting differences remain in migration 0043, application/distribution.py, tests/test_app.py and scripts/configure_publication_channel.py; untracked .tmp/design were not edited or included in release checks.
- All 26 Linux maintenance tests passed, including the Windows symlink skip. The newly built production API image is tested again in a disposable database before real migrations or restarts.
- Isolated PostgreSQL checks use only a copy of production schema and Alembic revision, never player/ticket/ledger data. Migration upgrade/check and transactional regression tests cover receipt/cancel races, historical Bingo key compatibility, frozen outcomes across payout rollback, concurrent settlement, retained future contributions, Bingo broadcast obligations and ledger conservation. A fresh-from-zero attempt exposed historical migration 0007's dependency on preseeded Daily; repairing that bootstrap chain is deferred outside this release.
- Published commits 67ae2da / 3ce75f9 under the VPS operations lock: database backup, API/bot/gateway rollback images, fresh-image PostgreSQL smoke, Caddy validation, migration 0054 and diagnostic archival before recreation all passed. Public HTTPS returned healthy Mini App/Admin, exact HTML and referenced assets; /web returns 410 and browser APIs return 404. The active gateway has no /srv/web and the server checkout has no frontend/web. Local Web source is retained. The independent legal-service root HTTPS route also remains available.
- Post-release read-only verification: API 1.56.1; WEB_ENABLED=false; migration 0054; account-versus-ledger mismatches 0, draws overdue by 10 minutes 0, underfunded committed jackpots 0, disposable audit databases left 0. Scheduler last success was 18 seconds old; independent host monitoring reports no warnings. No production test purchases, balance corrections or historical-data rewrites were performed.
- Rollback must retain committed pending outcomes: never remove the new protection or resume a service that generates replacement results for an already committed draw. Use a compatible forward fix if a pending outcome needs recovery.


## [API 1.56.0 / Mini App 1.66.1 / Admin 1.60.0] - 2026-10-11

- Owner approved priorities 1 and 2: recover purchases after connection loss/reload and monitor performance, errors, draws, publications, storage and backups. Releases: API 1.56.0, Mini App 1.66.1, Admin 1.60.0. No price/odds or completed financial history changes.
- Hardened stale cart checkout as well as persistence: consumed cart identifiers block a fresh POST and refresh the remaining positions, rather than charging a stale UI snapshot. Exact-key recovery remains available for an already pending request.
- Added a per-authenticated-user durable client request journal across scheduled games, Bingo and all instant games; read-only ledger receipt lookup, exact same-key retry, original-draw binding and cart consumption markers. Lost responses no longer become a fresh checkout after reopening. Storage failures prevent transmission; missing receipts are not treated as proof of failure.
- Explicit cancellation acquires the same PostgreSQL transaction advisory lock as durable purchases. It returns the existing receipt or persists a unique cancellation fence for an uncommitted request; late requests cannot charge it. Additive migration 0053_purchase_cancellations; no ticket deletion or silent balance corrections.
- Added bounded one-hour client/server p50/p95 timing/error metrics and periodic operational snapshots. Admin System/Health displays measured speed, warnings, disk, backup freshness, overdue draws and delayed publications. Backups and host watchdog state are mounted read-only; telemetry contains fixed metric labels, duration and status only.
- Added independent minute-based systemd watchdog for container health, public HTTPS health and freshness of API monitoring. It atomically replaces one redacted state file; no new Telegram messages or posts are sent. Release helper installs the timer under the existing operations lock and keeps diagnostic archival. Prebuilt gateway now includes the existing independent legal-service Caddy extension when rebuilding.
- Details and operational thresholds: docs/PURCHASE_RECOVERY_MONITORING.md. Verification: backend 535 passed/one Windows symlink skip covered by 26 Linux maintenance regressions; Mini App 166, Admin 46 and Web 35 tests passed; affected frontend lint/typechecks and all three production builds passed; Ruff and mypy (82 source files) passed. A disposable PostgreSQL backup restore passed migration upgrade/check, concurrent ×25 single-operation replay, four purchase/cancel races, foreign-owner receipt hiding and receipts for all three instant games. No production purchases were made during validation.
- Published 92135ee / 3b37066 / 284647e under the operations lock with database and rollback-image backups and diagnostic archival. An SSH interruption stopped the original full upload before source application; recovery used verified incremental archives (1.50 MB and 0.38 MB) and checked all 7,278 target hashes. Only API and gateway were recreated; the final cart guard used gateway-only publication and passed 51 focused Mini App tests plus lint/typecheck/build.
- Production verification: HTTPS health and exact deployed Mini App/Admin asset hashes passed, unauthenticated private endpoints returned 401, migration 0053 is active, financial-ledger mismatches/invalid indexes/disposable databases are all zero. Runtime and independent host monitoring reported no warnings, overdue draws or delayed posts; seven fresh database dumps are retained. The independent legal-service HTTPS route remains healthy. Journals are synchronized to the live API for the admin release-history view.
- Post-release centralized maintenance preserved the existing seven-dump/current-plus-two-image/512 MB cache policy, reclaimed another 1,232,424,960 bytes and passed health checks with no disk warning. Owned failed-upload and preflight artifacts were removed separately under the operations lock.

## Compact server-only storage policy - 2026-10-11

- Owner approved a maximum of seven database dumps on the VPS, current plus two prior rollback images, and a 512 MB unused build-cache target. Removed seven-day image and 48-hour cache age exemptions; source archives keep their separate newest-three policy. No computer transfer is configured.
- Centralized database dump pruning in maintenance with verified backup-volume identity, strict filenames, filesystem identity revalidation and retained-dump TOC checks. Backup creation now publishes only a validated atomic dump; failed partial creation preserves previous recovery points. Seven files include both nightly and pre-release copies, so this does not guarantee seven days of history.
- Image cleanup refreshes protected IDs under the operations lock and checks each image's tags, ownership and container references before non-forced removal, avoiding a full image scan per deletion. Added retention, invalid-dump, volume, new-reference/tag and cache-filter regressions. Scope excludes business rows, database data volume and unrelated images/services.
- Legacy intermediate parents required by protected images are preserved on Docker dependency conflicts; unused descendants are considered first. These shared parent layers are necessary image contents, not extra release versions. Local backend suite and types passed; Linux retention checks and a full isolated restore validate the release before completion.
- Published through f8098f6 and completed cleanup: 18,223,230,976 bytes reclaimed, filesystem 87%/5.2 GiB available to 41%/about 23 GiB (`df -h` rounded). Seven dumps total 480,327,645 bytes; nine tagged project release images remain (current plus two per service), alongside required parents/base/other-service images. Docker reports 382.6 MB unused build cache. Backend 523 passed/one Windows symlink skip, that case included in 26 passed Linux maintenance tests; Ruff, mypy and Linux shell syntax passed. Full disposable restore passed and was dropped. All seven container identities, protected rollback image identities and unrelated-file metadata remained unchanged; HTTPS healthy, timers active, financial-integrity/overdue/index checks all zero.

## Legal Mini App HTTPS integration - 2026-10-11

- Added a separate legal HTTPS virtual host on the existing gateway, proxying only to the independent legal service on the private Docker bridge. Existing lottery routes, containers and database remain independent. The gateway image includes the extension so future builds retain the route. Validation uses Caddy configuration checks and both applications’ health checks; no frontend code changed.

## Count-only release archive retention - 2026-10-11

- Owner approved keeping only the newest three known release archives per category, without the previous 14-day age protection. Counts are shared across `/opt/k-loto/backups` and `/opt/k-loto-backups`; unknown files, database dumps, business history and diagnostic-log retention remain independently protected.
- Added regressions for fresh archive expiry, shared categories/directories and zero/negative policy validation. Updated storage policy and explained audit priorities in plain language. Publication uses the operations lock and the centralized maintenance script's operations/backup locks; service rebuilds are unnecessary.
- Published bb3dab3; 17 Linux maintenance regressions and scoped Ruff passed. Cleanup removed 30 surplus archives and reclaimed 2,142,216,192 bytes: 92%/3.2 GiB available became 87%/5.2 GiB. Verified the retained newest-three identities per category and unchanged metadata for 18 unrecognized/protected files. HTTPS/API/database health and both timers passed; disk warning remains above 80%.

## Casper Aurora instant release - 2026-10-09

- Published dab17aa / 8058f6f as API 1.53.0, Mini App 1.63.0 and Admin 1.57.0 under the operations lock with database/source/image backups and archived diagnostics. Disposable PostgreSQL clone passed rollback, concurrent replay, separate game history, preservation of existing tickets and ledger settlement checks. Production confirms exact Aurora odds/price and scoped routes/history; Alembic check has no pending operations, API healthy, database container and Web assets preserved.
- Actual public Mini App 1.63.0 shows both instant games. Hero copy sits entirely above the crystal at 320/390/430 px with no overlap or overflow, per owner's correction. Browser hashes match built Mini/Web HTML and Aurora artwork. Admin HTML was verified on its configured separate Admin host; the release helper initially checked `/admin/` on the Mini host, which correctly serves the Mini fallback, so that final helper assertion was corrected by verification on the proper host. Intermittent local HTTPS transport retries did not change deployed assets. No real Aurora purchases were made during verification.
- OD-048 approved at 3,000 CAS, purchases of exactly 1 or 3; versioned Aurora odds are separate from immutable LIVE v1. Exact 10,000-roll distribution gives 40% any payout, 10% profit and expected 2,300 CAS (76.6667%). Retain instant ticket-cost burn and paired Fund/user prize ledger entries.
- Reuse immutable instant_tickets with stored odds_version as the game discriminator; no schema change or historical rewriting. Scoped API history, player filters, Admin player history and separate summary, plus platform per-game period counts. Cross-game idempotency namespaces and owner/quantity replay validation prevent accidental replay or duplicate charges.
- Added generated northern-lights crystal artwork with imagegen built-in. Aurora selection card and separate lazy screen, resumable 1.6-second hold, viewport/Telegram gesture lock, keyboard holding, reveal-all without another purchase, history and transport retry with original key/quantity. Reduced-motion support and authoritative server settlement.
- Checks: backend full suite plus corrected Admin fixture rerun covers 448 passing / 1 Windows symlink skip; mypy 75 files; scoped Ruff passes. Mini App full suite plus updated catalogue fixture rerun covers 140 passing; Admin 38 passing. Affected frontend lint/typecheck/build; built smoke 320/390/430, three synthetic tickets, partial hold and reveal-all. Release includes disposable PostgreSQL backup-clone accounting/concurrency/rollback/history checks.

## Casper Grand flagship implementation - 2026-10-09

- Published ea70613 / 6c13062 under the VPS operations lock with database/source/image backups and archived diagnostics. PostgreSQL backup-clone rollback, concurrent idempotency, completed-history, balanced-refund and new-format purchase checks all passed. Activation refunded exactly 145 tickets / 4,865,000 CAS and converted three future draws; production confirms 290 zero-sum ledger entries, all REFUNDED rows preserved and all future snapshots updated. Existing auto-play can create new-format tickets after restart. Stored legacy name remains Kasper Grand through bootstrap; presentation alias remains Casper Grand.
- API 1.52.0 / Mini App 1.62.0 / Web 1.56.0 public HTTPS health 200, exact built Mini/Web HTML and Grand artwork verified; Alembic check has no pending operations. Admin assets and database container unchanged. Actual public built UI verified at 320/390/430 with seven columns and no overflow; server dashboard exposes all ten new fixed payouts. Built Web smoke at 390/1240 also passes without overflow. Preview draws are isolated synthetic data and perform no real purchase.
- OD-047 approved: versioned grand_fixed_5_35_2_5 with ten fixed per-ticket prizes, shared 5+2 jackpot, unchanged price/schedule/funding. Legacy percentage rules remain available for historical snapshots. No schema change.
- Generalized the audited Halloween transition service, preserving its defaults. Grand activation requires the configured admin audit identity, chronological recovery, transactional locks, original-price paired refunds and per-ticket audit; repeat activation is a no-op. Owner approves 145 future tickets / 4,865,000 CAS.
- Brighter generated Grand Hall artwork, tactile medallions, removable racks, accessible pressed states and reduced-motion support. Shared pure controls avoid duplicate React hook dispatchers. Explicit seven-column specificity survives production CSS order. Perspective animated draw uses server-revealed numbers. Catalogue footprint unchanged.
- Checks: backend 441 passed / 1 platform skip; mypy 75 files; scoped Ruff passes (759 existing repository findings outside scope). Mini App full run plus corrected focused rerun covers 137 tests; Web 35 / Admin 38 pass. Frontends lint/typecheck/build pass. Built Mini App smoke at 320/390/430 confirms seven columns, field limits and removal. Release checks PostgreSQL rollback/concurrency/history/refunds against a disposable backup clone.

## Casper Grand concept study — 2026-10-09

- Discussion only at the owner's request: recorded lower payout preferences and unresolved senior tiers in OD-047 and `archive/reference/design-studies/archive/reference/design-studies/docs/CASPER_GRAND_CONCEPTS.md`. Evaluated the proposed fixed table's ordinary payout expectation (7,320.60 CAS / 14.64% of a 50k ticket), excluding jackpot and refill; fund coverage is not approved by this calculation.
- Generated three full number-selection screen concepts with imagegen: Grand Hall, official Casper Loto brand reference, Golden Orbit. Saved previews in `archive/reference/design-studies/grand-concepts-2026-10-09/`; inspected all main grids (1–35) and secondary fields (1–5). These are nonfunctional design studies. The production logo asset remains unchanged. Owner requests a 3D animated draw with no video inserts; no implementation or production release is authorized in this study.

## Halloween production grid cascade regression — 2026-10-09

- Owner screenshot exposed one-column stretched number controls despite the deployed 1.61.1 assets. Vite production CSS ordering let the equal-specificity generic `.ticket-number-grid` rule override Halloween's seven columns with an unset `--columns`. Development screenshots missed this cascade.
- Raised the Halloween field selector specificity, made its grid display explicit and supplied `--columns:7` defensively. Verification uses the built production preview, including a late generic stylesheet injection to reproduce the original cascade, at 320/390/430 px.
- Mini App 1.61.2 / Web 1.55.2 lint/typecheck/build passed. Published implementation 7f58680 with gateway-only restart, operations lock and database/source/image backups; API/bot/database identities and Admin assets are unchanged. Browser verified the actual public 1.61.2 build at 320/390/430 px with a late generic grid rule: all 28 buttons occupy seven columns without overflow, and three selections render as pumpkins. Screenshot `archive/local/2026-10-20/check-artifacts/halloween-production-1612-confirmed.png` comes from production in the isolated broadcast preview (no real purchase). Internal health passed; release helper additionally verifies public HTML, bundles, version and HTTPS health.
- First publication automatically rolled back after external HTTPS handshake timeouts during the file sweep, with no asset mismatch found. Repeated the locked publication with bounded per-request transport retries; all public Mini App/Web HTML and JS/CSS hashes, version 1.61.2 and health 200 passed. Rechecked the seven-column grid on the final public build.

## Halloween pumpkin number field correction — 2026-10-09

- Replaced the selected-circle CSS approximation with decorative SVG pumpkin bodies: sculpted ribs, curved stems, warm highlights and glow. Shared ticket component updates Mini App and Web; added an inset field matching the approved first concept. Number text, accessible button state, keyboard operation and selection/purchase services remain unchanged.
- Scoped verification: affected frontends lint/typecheck/build; TicketComposer regression (8 tests), Web Halloween host regression (2 tests); browser smoke at 320/390/430 px confirms seven columns, no horizontal overflow, three pumpkins in the field and removable selected pumpkins. Actual screen: `archive/local/2026-10-20/check-artifacts/halloween-pumpkin-fix-390.png`. The decorative component uses parent-supplied SVG IDs so the Web shared-source import does not load a second React hook dispatcher.
- Published implementation 90a5888 as Mini App 1.61.1 / Web 1.55.1 under the operations lock with database/source/image backups. Only gateway restarted. Public HTTPS verified version 1.61.1, exact Mini App/Web HTML and every built JS/CSS bundle, brand asset and health 200. Admin fingerprint and API/bot/database container identities are unchanged.

## Casper Halloween format and pumpkin experience — 2026-10-09

- Owner approved Casper Halloween, 3/28, 6,666 CAS price, 28,000 CAS for exactly two matches, no one-match payout, original bat decoration and first pumpkin art direction (OD-046). Schedule, base jackpot and existing funding/sharing remain unchanged.
- Added versioned `halloween_3_28`; retained `grob_3_16` for immutable settled history. No schema change is needed. Financial activation is an explicit application-service operation, not an automatic migration that could silently refund tickets during startup.
- Added atomic owner-authorized refund/activation service with lottery/draw/ticket/account locks, per-ticket zero-sum TICKET_REFUND pairs, idempotency keys, ticket/draw/lottery audit, source snapshot checks and due-draw recovery prerequisite. No ticket deletion or direct balance replacement. Uses the existing configured Admin Panel audit identity with `is_admin`; player privileges are unchanged.
- Generated and saved the pumpkin production asset with imagegen (381 KB WebP). Added genuine React number controls, selected lanterns, original SVG bat decoration, server-supplied fixed payouts, preserved random ×1/×5/×25 actions and repeat/favorite behavior. Old/refunded ticket detail preserves the old 16-number field and displays refund rather than a losing result. Live format comes from the draw snapshot.
- Checks: backend 426 passed / 1 Windows symlink check skipped; Mini App 136 passed; Admin 38 passed; Web 34 passed; backend mypy passed. Existing publication-channel unit tests now stub transport-state storage rather than unexpectedly requiring local PostgreSQL. Changed-file Ruff passes; full `scripts/check.ps1` stops on 759 pre-existing Ruff findings outside this change. All frontend typecheck/lint/build passed; isolated VPS PostgreSQL checks precede financial activation.
- Stabilized the Web balance callback so parent renders cannot restart dashboard polling; regression verifies callback replacement. First isolated PostgreSQL run caught a keyword-only invocation error in the smoke script; source/images rolled back before any production transition. Corrected the script and repeated the locked release.
- Web 1.55.0 shares the React pumpkin presentation while retaining its existing durable pending-purchase hook. Removed the fixed 16-number compatibility guard in favor of comparing refreshed server parameters with the opened draw; original legacy Phaser code/assets remain in source for historical reference. Web smoke verified 390/1240 px, three-number purchase containing 28; CSS explicitly protects the seven-column grid and checkout positioning from shared-style import order.
- Browser smoke: 320/390/430 px, seven columns without overflow, three-number cap, removable lanterns, random ×25 purchases, reduced motion and festive catalogue return. `archive/local/2026-10-20/check-artifacts/halloween-selected-390.png` and `archive/local/2026-10-20/check-artifacts/halloween-catalog-390.png` capture the actual UI.
- Published implementation f43c840: API 1.51.0 / Mini App 1.61.0 / Web 1.55.0 under `/run/lock/k-loto-operations.lock`, with source/image/database backups and archived API/bot diagnostics. Isolated PostgreSQL rollback, concurrent idempotency, balanced refunds, unchanged completed history and new 3/28 purchase all passed before activation. Production refunded 90 tickets / 599,940 CAS and converted two future draws; 180 compensating ledger records sum to zero, refunded tickets remain stored. Production API confirms 3/28, 6,666 CAS and {2: 28,000}; future snapshots use the new rules. Alembic check reports no schema drift; API/database are healthy, HTTPS health 200, exact Mini App/Web HTML and pumpkin asset verified. Admin asset fingerprint and database container identity are unchanged. Release archive/backups are retained in `backups/halloween-1791501206` and the configured VPS backup directories.

## Compact visual catalogue and festive filter — 2026-10-09

- Replaced the full-width jackpot-sorted list with a stable editorial two-column grid (three columns on wider screens), compact illustrated cards, raised frames, accent light and reduced-motion-safe hover depth. Reused existing game assets; no new engine or raster downloads. Price/jackpot remain server values; LIVE keeps its existing price and states symbol-based winnings without inventing a jackpot.
- Added All / Instant / Draw / Festive filters; only grob is assigned festive in this release, with overlap in All and Draw. Integrated Fast into the unified catalogue while retaining its dedicated destination. Grand has an equal-sized card with a weekly badge. Filters and scroll are preserved on return, including Fast and LIVE; lazy catalogue loading is separated from the draw-room/live bundle.
- Verification: full Mini App suite 135 passed; catalogue tests cover overlapping categories, stable order, server amounts, Moscow times, empty/unknown entries and deferred scroll restoration. App regression covers festive/Fast return; updated old Dual count assertion to its existing 2 / 2 display. Chromium at 320/390/430px confirmed no horizontal/card/filter overflow, keyboard opening, reduced-motion setting, LIVE/festive returns and Fast scroll restoration (864px before/after). Final lint/typecheck/build and affected regression rerun recorded in local logs.
- scripts/check.ps1 was attempted once and stopped on 759 existing Ruff errors in unrelated .tmp scripts/backend migrations; subsequent backend/admin/web checks were not reached. This UI-only release follows the scoped frontend publication policy in AGENTS.md. Native Telegram device testing is unavailable in this session.
- Published Mini App 1.60.0 (implementation 74e8dd3) under /run/lock/k-loto-operations.lock with production database/source backup, local incremental release archive and gateway rollback image. Final lint/typecheck/build and 40 affected tests passed after scroll-state refinement. Public HTTPS verified version 1.60.0, exact HTML and catalogue JS/CSS, brand asset and health 200; internal API/database healthy. Only gateway restarted; Web/Admin hashes and API/bot/database identities unchanged. The archive preserves the unchanged nested artwork library. Final browser capture confirmed saved/returned scroll 854.4px (the automation scrolls slightly when clicking a card).

## Stage 1: scratch and Stories gesture fixes — 2026-10-08

- Added a shared reference-counted viewport lock that freezes the body at its current scroll position and restores inline styles/scroll on release, cancellation and unmount. Native Telegram vertical swipes are disabled before interaction while LIVE is open and while Stories are visible; unsupported clients retain browser protection, previously disabled swipes remain disabled.
- Kept all LIVE reveal paths and server purchase/settlement behavior. Scratch distance survives separate strokes, pointer-up now ends the gesture, cancellation does not reveal a ticket. Stories retain tap/swipe navigation and press-to-pause without the pause icon; background time no longer consumes the remaining story duration.
- Verification: affected regression suite 19 passed; Mini App lint, typecheck and production build passed. Chromium at 390x844 confirmed stable scratch bounds, restored scroll, button/tap reveal, hold beyond seven seconds and downward dismissal with mocked Telegram/purchase data. Native Telegram Android/iOS device testing is unavailable in this session.
- Full Mini App suite: 127 passed, one pre-existing Dual assertion failed at App.test.tsx:671 (expects the old “2 из 2” text); App/Dual implementation and test are unchanged. scripts/check.ps1 was attempted and stopped at Ruff with 759 existing errors across unrelated .tmp scripts/backend migrations; later backend/admin/web checks were not reached. Per AGENTS.md frontend-only policy, unrelated failures do not block this scoped gateway release.
- Published Mini App 1.59.3 (implementation commit 09dfa3b) under /run/lock/k-loto-operations.lock using the existing gateway-only helper. Local release and downloaded previous-source backups are retained in backups/miniapp-1.59.3-1791485996; production database/source backup and rollback image were created before upload. Gateway configuration validated and only gateway restarted. Public HTTPS confirmed version 1.59.3, exact built HTML, brand asset and health 200; internal API/database healthy, Web/Admin hashes and API/bot/database container identities unchanged.

## Casper Dual circular ticket restoration — 2026-10-06

- Replaced the generic Dual number grid with two fixed-position 12-number dials in the Mini App. Reused the existing night/dawn scene and added lightweight CSS-only metal/glass depth, selection glow and reduced-motion handling. Purchase rules and server state are unchanged.
- Regression test verifies twelve stable positions per dial and the two-number cap. Mini App lint, typecheck, focused 7-test suite and production build passed. Browser preview at 375px and 320px confirmed the number buttons remain within each dial, with no position shift on selection.
- Published Mini App 1.59.1 through the locked gateway-only release: production database backup, upload, rollback image, diagnostic archive and gateway restart succeeded. Production health check passed; API and database remained healthy.

## Owner-authorized publication activation — 2026-10-06

- Added collection of verifiable A jackpot/result/winner/sales facts and scheduled statistical drafts to the existing Publication/event-state engine. Reconstruct historical B milestone crossings and jackpot records from immutable timestamps/ledger, with per-event keys, pre-window baselines and no A/B merging. No financial history is changed. Unspecified unusual/large/activity/anniversary criteria remain excluded.
- Compiled the owner's 170 A/B copy variants into inert package data and added raster rendering of existing approved artwork with Cyrillic fonts. Durable JSONB outbox commits an in-flight claim before Telegram I/O, stores message IDs, retries only definitive Telegram throttling and blocks uncertain delivery. Production enabling requires a prepared persisted historical window. No secrets enter snapshots/logs.
- Owner overrides: historical posts from 25 September through captured current cutoff include calculated drafts and have no editorial spacing. Subsequent automatic posts retain 1,800 seconds, manual approvals do not affect that interval. Mini App shows at most ten source-fresh news items, including approved latest replay items before the Telegram queue reaches them. Product/manual changes are never invented.
- Verification is deliberately scoped at owner's request: publication unit/regression tests, changed-service lint/typecheck, affected frontend builds and focused Story behavior; restored PostgreSQL replay/render/fake-transport deduplication and uncertain-outcome smoke before actual activation. Deployment and real send results will be recorded after execution.
- Initial full historical clone replay exceeded its stage timeout while performing per-row inserts/updates; the exact disposable clone was stopped and removed without production mutation. Collection now primes existing keys/states under the shared event lock and batches new inserts. Release verification uses a 30-minute history sample plus real statistics/rendering and fake transport; the production job keeps the entire owner-authorized window.
- Published API 1.50.0 / Mini App 1.59.0 / Admin 1.56.0 under the VPS operations lock with database/source backups, rollback images and diagnostic preservation. API/database healthy and migration 0049 has no drift. Scoped backend regression suite: 34 passed; cache changes: 21 passed; changed-service lint/typecheck and both frontend lint/typecheck/build passed; Story behavior: 4 passed. Disposable PostgreSQL sample rendered 9 event types, confirmed key deduplication and blocked retries after simulated uncertain send.
- Actual owner-authorized production replay prepared 17,291 separate posts for 2026-09-25 00:00 MSK through 2026-10-06 03:42:08 MSK, then channel permission was verified and durable transport enabled. First read-only proof confirmed 40 real messages sent, 17,251 queued, 10 fresh Stories and first channel message ID 5 for the event at 25 September 00:00:22 MSK. No uncertain sends at that observation. Existing 20 pre-window nonvisual candidates stay outside the authorized replay. Source backups include publication-automation-2026-10-06-source.tar and publication-automation-2026-10-06-optimized-source.tar. Historical delivery continues without editorial spacing; ongoing automatic interval remains 1,800 seconds.

## Owner platform B artwork and copy — 2026-10-06

- Imported all ten owner PNGs with provenance, deterministic paired compiler and real React preview generator. Added 180 B choices to the existing catalog; all 2,130 A records preserved byte-for-byte as serialized objects. Optional center alignment in both identical renderers retains legacy A positions; B has a central text cluster and central Story CTA. Platform manual drafts use existing workflow and catalog navigation without a fake lottery entity. Nonvisual B guards and delivery-disabled policies remain intact.
- Imported the supplied A text verbatim (80 variants), retaining one wording concern in OWNER_TEXT_REVIEW.md. Prepared 90 editable B variants with explicit ticket/player distinctions, draft modes, placeholders, stable hashtag mapping and spoiler instructions. No text or images sent to Telegram. API 1.49.1, Admin 1.55.7, Mini App 1.58.7.
- Verification: backend lint/typecheck passed, full backend suite 335 passed / one Windows symlink capability skip; Admin 36 tests and Mini App 118 tests passed, both typecheck/lint/build passed. Inspected actual React-rendered overview of all ten Story/Post pairs; client renderer/assets identical and all A objects unchanged.
- Published API/gateway with a 30.34 MiB scoped overlay under the complete VPS operations lock: database/overwritten-file backups, rollback images, restored disposable PostgreSQL verification including actual platform visual draft/publish, diagnostic archive and production health/schema checks. Production catalog is 2,310 (2,130 A unchanged plus 180 B); zero published visual rows and Telegram delivery disabled. Both HTTPS clients match built HTML and all twenty new images exactly. API 1.49.1 / Mini App 1.58.7 / Admin 1.55.7; migration 0049, no schema drift, API/database healthy, 18 GiB free. Final copy wording distinguishes a crossed milestone from an exact current total. Source backups: backups/platform-b-visuals-2026-10-06-source.tar and backups/platform-b-visuals-2026-10-06-verified-source.tar.

## Platform publication event foundation B — 2026-10-06

- Extended existing Publication storage/workflow with nullable event type/key/mode, unique dedupe and content-only checkpoint table, migration 0049. Exact requested B registry; configurable continuation grids, read-only platform metrics including instant purchase/win tickets and Fast draws, absolute current jackpot record with immutable-history baseline, refreshable one-day jackpot aggregate, explicitly requested B3/B4 drafts. Existing A catalog/feed remains unchanged and nonvisual events cannot publish through visual endpoints.
- Added authenticated/CSRF-protected admin event APIs and isolated scheduler reconciliation at approved Moscow slots; exceptions cannot interrupt draw recovery. Automatic eligibility remains distinct from persisted draft/delivery state. Future common pacing is 30 minutes with manual bypass, no daily cap and separate A/B batch keys; dispatcher/renderer/texts and automatic A detection are not present or activated by this backend-only phase.
- API 1.49.0. Also resolved pre-existing Dual typing errors with protocol/casts only and a pre-existing bot string-length lint issue without runtime changes. Verification: backend lint/typecheck passed, 333 tests passed with one Windows symlink capability skip; all three frontends typecheck/lint/build passed and 185 frontend tests passed. Mini App passed on a single-worker retry after parallel test contention. Owner-edited Telegram text file excluded.
- Published only API with a 149 KiB scoped overlay under the full VPS operations lock: production database/overwritten-source backups, rollback image, isolated fresh restored PostgreSQL clone, migration/check and concurrent scan/draft smoke, production migration, diagnostic archive, restart and health verification. Isolated fixtures were discarded with the disposable database. Production confirms API 1.49.0, migration 0049 with no schema drift, 18 supported event types, 21 persisted B candidates all unpublished, separate visual feed, all 2,130 A templates retained, 1,800-second future pacing/no daily cap and delivery disabled. Scan checkpoint recorded; no instant smoke fixtures in production. API/database healthy, 19 GiB free. Source backup: backups/events-b-2026-10-06-source.tar.

## Atmospheric additions for remaining draw games — 2026-10-06

- Owner requests complete atmospheric scenes and then explicitly corrects scope to additive artwork, retaining existing templates. Generated eight independent images with the built-in image_gen tool: imperial Grand hall/gardens, nocturnal 2:22 cloister/library, Ball ballroom/lakefront terrace, gothic ГРОБ castle/garden. Source WebPs, prompt set, provenance, overview and deterministic paired compiler included; no typography baked into source art.
- Preserved all 1,874 previous draw-game catalog entries exactly; added 256 game/event choices sharing sixteen backgrounds. Instant LIVE excluded from selectable publications only; original files/snapshots and game mechanics preserved. Catalog total 2,130. Mini App 1.58.6, Admin 1.55.6, API 1.48.6. Verification: all eleven publication tests passed, backend test lint passed, both affected frontends typecheck/lint/build passed. Dimensions, text zones and identical client bytes verified; 3.91 MiB per client. Source artwork and paired overview inspected. Real Admin renderer with local mocked API loaded all eight pairs, retained four old A1.1 choices alongside two new choices per game, excluded LIVE and had no horizontal overflow at 390px.
- Published API/gateway with a 28.40 MiB overlay under the complete VPS operations lock; database and overwritten-file backups, rollback images and pre-restart diagnostic archive completed. Production confirms 2,130 templates, all 256 additions assigned to the four intended games, LIVE excluded and zero publication rows. Both HTTPS clients match built HTML and sampled new backgrounds for each game plus a legacy Grand asset. Mini App version 1.58.6, API/database healthy, migration head 0048, 20 GiB free; permanent channel delivery remains disabled. Source backup: backups/atmospheric-2026-10-06-source.tar. Owner-edited text file excluded from release.

## Casper Dual owner-only publication library — 2026-10-06

- Replaced all 66 old active Dual template choices with five supplied day/night scenes, paired Story/Post layouts and editable copy zones. Source provenance, manifest, paired overview and deterministic compiler added to the full pipeline. Old hashed background files retained for immutable saved publication snapshots; all 1,746 other-game entries preserved exactly. Catalog total 1,906, with 160 Dual scene/event choices sharing only ten backgrounds per client.
- Versions: Mini App 1.58.5, Admin 1.55.5, API 1.48.5. No automatic rules, channel sends or draw mechanics changed. Verification: focused backend catalog/snapshot regression and both affected frontends typecheck/lint/build passed. Exact other-game preservation, all ten background dimensions, text-zone bounds and matching client bytes checked; 2.02 MiB per client. Paired overview inspected; real Admin renderer with a local mocked API loaded all five pairs, offered five A1.5 choices and had no horizontal overflow at 390px.
- Published API/gateway with a 16.70 MiB overlay under the full VPS operations lock, database/overwritten-file backups, rollback images and diagnostic archive. Authenticated production catalog confirms 1,906 entries and 160 owner-only Dual choices; zero publication rows, channel delivery disabled. Both public HTTPS clients exactly match built HTML and sampled new/legacy backgrounds. Mini App version 1.58.5, API/database healthy, migration head 0048, 20 GiB free. Source backup: backups/dual-2026-10-06-source.tar. Owner-edited Telegram text file excluded from this release.

## Additional owner Fast publication scenes — 2026-10-05

- Added six supplied scenes strictly in attachment order: 56-6/54-5 CODE (technical shadow), 53-4/52-3 FLASH, 50-2/48-1 PULSE. Paired 9:16/4:3 layouts and separate editable text, game-specific palette and sans-serif typography. All previous 1,620 entries remain unchanged; 192 additional scene/event choices share just 12 backgrounds per client. Source hashes, assignment manifest and paired overview stored. Compiler added to full pipeline.
- Versions: Mini App 1.58.4, Admin 1.55.4, API 1.48.4. No automatic rules, channel sends or lottery mechanics changed. Verification: focused backend catalog/snapshot regression passed; both affected frontends typecheck/lint/build passed. Exact preservation of all 1,620 previous entries, exclusive two-scene game assignments, all twelve raster dimensions and matching client bytes verified; 1.64 MiB added per client. Paired overview inspected; real Admin renderer with local mocked API loaded all six pairs, kept four prior A1.1 choices per game and has no horizontal overflow at 390px. Published API/gateway with a 14.61 MiB overlay, full operations lock, database/source backups, rollback images and pre-restart diagnostic archive. Authenticated production catalog confirms 1,812 entries and 192 new Fast choices, zero publication rows, channel delivery still disabled. Public HTTPS checks passed for a new background of each Fast game plus existing Bingo art on both clients; HTML exactly matches builds, Mini App version 1.58.4, API/database healthy, migration head 0048 and 21 GiB free. Source backup: backups/fast-2026-10-05-source.tar.

## Casper Bingo owner collection replacement — 2026-10-05

- Owner authorizes replacing the existing Casper Bingo library with all ten supplied emerald/gold scenes. Added source provenance, manifest, paired overview and deterministic Bingo compiler, integrated into the full asset pipeline. Removed 66 old Bingo templates from active selection; retained old hashed files for immutable publication snapshots. All ten scenes are offered for every existing Bingo A label, including A1.1 jackpot and A1.5 jackpotless series; no unused artwork.
- Catalog now has 1,620 entries (1,300 other-game entries exactly preserved, 320 Bingo scene/event choices), backed by only 20 new shared background files, 2.94 MiB per client. Versions: Mini App 1.58.3, Admin 1.55.3, API 1.48.3. No financial rules, event automation or channel sends changed.
- Verification: one focused backend catalog/snapshot regression passed, both affected frontends typecheck/lint/build passed; all ten paired choices loaded in the real Admin renderer with mocked local API, A1.5 has ten options, 390px has no horizontal overflow. Exact other-game data preservation, dimensions, text-zone bounds and matching client asset bytes checked; paired overview inspected. Published API/gateway using a 22.45 MiB overlay under the shared VPS operations lock with database/overwritten-source backups, rollback images and diagnostic archive. Production authenticated catalog confirms all 320 Bingo choices and no old selectable Bingo templates; 1,620 total, zero publication rows, channel delivery remains disabled. Both public HTTPS clients match built HTML and sampled new/legacy Bingo backgrounds; Mini App version 1.58.3, API/database healthy, migration head 0048, 22 GiB free. Local source backup: backups/bingo-2026-10-05-source.tar.

## Expanded editable Telegram copy bank — 2026-10-05

- Expanded `archive/reference/retired-publications/docs/publications/block-a/telegram-posts.v1.txt` from 30 to 80 Telegram caption variants: eight for each A1/A4 block, with different lengths and sentence rhythm while preserving the existing placeholders and A4.4/A4.5 status labels.
- Verification: 80 unique caption IDs, eight variants in each of the ten blocks, UTF-8-readable text, and no runtime or schema changes.

## Editable Telegram post bank and launch checklist — 2026-10-05

- Created UTF-8 text file docs/publications/block-a/telegram-posts.v1.txt with all 30 prepared A1/A4 Telegram captions, stable variant IDs and explicit pending/excluded labels for A4.4/A4.5. No Story fields; no new editorial claims or automatic rules. Owner can edit and return this file for review; A2/A3/A5/A8 bank remains outstanding.
- Updated archive/reference/retired-publications/docs/PUBLICATIONS.md with actual delivery status, the single authorized channel test and approved-but-unimplemented Story lifetime. Added concrete manual-delivery and automatic-event launch checklist based on current service/renderer/scheduler code.
- Verification: exactly 30 caption IDs exported, readable UTF-8 file, documentation diff checked. No runtime change, channel send or production release.

## Block A participant-record threshold — 2026-10-05

- Owner approves A4.3 only with at least 500 unique participants per draw and at least 20% growth over the previous record; both thresholds inclusive. Updated editorial policy and OD-039. This records a business decision only; automatic delivery remains disabled. Documentation diff checked; no runtime change or deployment.

## Block A schedule clarification and readable texts — 2026-10-05

- Owner confirms Mini App Stories and permanent Telegram posts; native Telegram Stories excluded. Fixed event checks at 12:22, 18:35 and 22:22 Europe/Moscow, immediate automatic publications after each scan, no spacing/daily cap. Removed already-approved formats/grouping from pending decisions; distinguished unimplemented delivery from unanswered business rules.
- Added docs/publications/block-a/texts.v1.md with all 30 existing copy variants, separate Story fields and Telegram body. Proposed A5 weekdays/rotation and clarified series/A4 thresholds and ticket counters for owner response; proposals remain inactive.
- Subsequent owner replies approve series thresholds every 50 draws / 200 Fast, A5 Monday/Wednesday/Friday at 12:22, rotation excluding last 3 images / 2 texts with oldest-used fallback, and inclusive sales milestones per draw only. Cumulative A4.5 copy preserved but excluded; A4.4 and minimum participant-record threshold await definition.
- Verification: generated readable bank contains exactly 30 variants. Documentation/editorial preparation only; no runtime, deployment or channel messages changed.

## Manual Stories and publication foundation — 2026-10-05

- Owner authorizes implementation in Admin/Mini App and explicitly postpones automatic rules. Added PublicationService, authenticated/CSRF-protected editorial endpoints and migration 0048. Server-owned template snapshots, field bounds, revision checks, transactional row locks, idempotent UUID draft creation/state retries and existing admin audit records. Published content cannot be edited in place; archive preserves content/history. No money/draw/auth rules, scheduler callbacks or personal notifications changed.
- Integrated all 758 pairs as hashed runtime WebP backgrounds (71.68 MiB per client, 143.35 MiB for both static bundles; catalog 0.71 MiB). Editable masters, full design sheets and visual experiments stay local. Old background hashes are retained when adding templates; Mini App receives only bounded published pages, not the full catalog. Draft edits/preview use shared safe-zone metadata and deterministic text layout, with independent Story/Post compositions and browser PNG export.
- Admin adds Stories/posts editor, save/publish/archive/copy workflow, independent channel caption and read-only permission check. Mini App rectangular news strip appears above the nearest draw, with native accessible Story dialog, swipe/arrows/manual controls and existing game navigation CTA (44px minimum touch region). Feed loads on Home mount and on explicit pagination/retry; no polling/publication job or automatic expiry.
- Owner supplied @casper_loto; existing @Kasper_loto_bot post/edit permissions verified and destination stored under VPS operations lock. No messages sent, second polling consumer, token duplication or channel delivery added. archive/reference/retired-publications/docs/PUBLICATIONS.md describes usage, connection inputs, snapshot architecture and deferred channel adapter; OD-036 records the current scope.
- Verification: full backend suite passed 314 tests with one existing Windows symlink skip after assigning a repository-local temp directory; 13 focused publication/channel checks passed. Full Admin suite 35 and Mini App suite 118 tests passed; both affected lint/typechecks passed. New Python paths pass Ruff and strict mypy; whole backend Ruff retains the pre-existing telegram_bot.py line-length violation and full-project mypy retains three pre-existing dual.py findings. Browser smoke uses synthetic data only: server draft/publish preview, read-only published fields, 1200×900 PNG export, mobile news placement, keyboard/Escape/navigation, CODE CTA and no horizontal overflow at 390/320 px. Real Telegram-device smoke unavailable. No synthetic content published to production/channel.

- Published Mini App 1.58.0 / Admin 1.55.0 / API 1.48.0 from e40db88 with local source backup and VPS database/rollback backups. Shared operations lock held across upload/build/migration/diagnostic archival/restart/health; only API and gateway recreated. Alembic 0048 is head and schema check reports no pending operations. Public HTTPS HTML and sample Story asset match local builds exactly on both hosts; authenticated API returns 758 templates and zero publication rows, rejects anonymous feed access and confirms channel permission with delivery disabled. Runtime background directories allocate about 75 MiB per client; VPS has 24 GiB free. Bot/database containers were not recreated.

## Category A lottery publication visual library — 2026-10-05

- Added isolated design/publications/category-a/ library for A1/A2/A3/A4/A5/A8 using the existing twelve game identities, source artwork and approved Casper symbol. Game palettes dominate; the older ten generic classic designs remain separate. No production frontend, business service, database, scheduler, auth or Telegram delivery changed.
- Each draw lottery receives 66 paired templates; instant Casper LIVE receives 32 compatible pairs, excluding accumulating jackpot, draw/schedule and draw-scoped record scenarios. 758 templates / 1,516 Stories and Post compositions cover all 32 requested subcategories; A1.1 has four compositions and other events two. No A6/A7, new-game launch, seasonal or standalone brand/service content.
- Exports include editable filled/background/zone SVGs, full-resolution WebP and lightweight previews, per-game/all-game PNG sheets, source provenance and exact field/CTA geometry. Placeholder copy only. Every Story has a lower CTA component linked to the technical game code; a real Mini App URL resolver and final label are explicitly deferred. Opaque game-colour text surfaces prevent artwork competing with copy.
- Added local filterable gallery with pagination, safe-zone mode, file downloads and keyboard-accessible native preview dialog. OD-035 records visual scope and the absence of business trigger decisions. Publication mechanisms are not implemented, as explicitly requested.
- Verification: Mini App lint/typecheck/build and generator/gallery/validator syntax checks passed. Artifact validator checked all 758 pairs, 1,516 full-resolution rasters and previews, 4,548 editable SVGs, all 32 subcategories, original asset hashes, exact dimensions, non-overlapping text zones and game-bound CTA geometry; all SVGs also parsed as XML. Browser smoke loaded all twelve game identities, all six categories, jackpot/composition filters, pagination, zone SVGs, modal CTA target and all eight download links. Gallery/dialog have no horizontal overflow at 390 and 320 px; Escape closes the native dialog and returns focus. No console errors after adding the local favicon. Comparison sheets and desktop/mobile screenshots preserved. This isolated artwork stage has no production feature change or deployment.

## Classic publication collection and chosen home placement — 2026-10-04

- Owner selected compact rectangular Mini App news covers above the nearest draw; moved the prototype strip and recorded that decision in OD-034. Player Web remains excluded; channel posts stay in scope.
- Added ten distinct universal classic compositions in the approved navy/ivory/gold palette, including three ivory variants. Each includes a 1080×1920 story background and 1200×900 post background in editable SVG and PNG, generic filled PNG examples, text-zone SVGs and a coordinate manifest. Art and copy occupy separate regions; templates are selectable independently of events.
- Added a gallery with zone overlay, background downloads and editable text previews. Standalone deterministic generator uses local sharp and approved unchanged logo derivatives. Prototype remains isolated from production and channel delivery.
- Verification: syntax checks and SVG/PNG generation passed; all 40 background/example PNGs match their specified dimensions, and every manifest text zone stays within its canvas and outside the illustration region. Browser smoke checked all ten designs with a long headline at 320 px, all four views at 390 px, light/dark copy, zone toggling, template retention across event changes and story navigation. No console errors or missing assets. Screenshots and the ten-pair comparison sheet are preserved. No frontend runtime or production release changed.

## Mini App stories and channel publication design study — 2026-10-04

- Added isolated, dependency-free design/publications/ prototype with three editable synthetic examples, separate story/channel/home compositions, coordinated decorative variants and annotated text zones. Uses approved Casper logo derivatives and navy/ivory/gold palette.
- Compared compact and larger news strips after the next-draw card; native dialog provides manual story navigation, Escape and keyboard arrows. Copy is assigned as text, draft edits survive tab/example switches and reset on reload. No production UI, API, Telegram delivery or business state changed.
- Owner clarified scope: Mini App plus Telegram channel; player Web excluded. Remaining product policies are recorded in OD-034. This is a design study rather than a completed product release; production installation follows the owner's layout/policy decisions.
- Verification: JavaScript syntax check and Mini App lint/typecheck/build passed; Vite build required elevated local filesystem access after esbuild hit the Windows parent-directory sandbox restriction. Browser smoke at 1440, 390 and 320 px covered all views, editable copy synchronization/escaping, draft retention across switches, visual variants, dialog previous/next and long-text layout. No console errors or failed image loads. Preserved comparison and three example PNGs beside the editable source. No product release or production/channel publication was performed for this isolated design artifact.

## Compact home archive entry — 2026-10-04

- Fixed an unconstrained SVG growing the Home archive button. Matched the latest-jackpot surface, fixed the icon at 42 px, removed extra vertical margins and retained the Home section gap. CSS only; no archive logic or other interfaces changed. Minimal verification: Mini App typecheck/lint/build and focused mobile visual smoke; gateway-only publication with backups and health verification.

## Mini App draw archive — 2026-10-04

- Added authenticated read-only archive service and Mini App endpoint, with completed-only standard scope, historical ruleset field metadata, recorded jackpot events and stable date/UUID cursor pagination (30 rows, maximum 50). No ticket scans, total counts, background polling, database writes or schema changes. Inactive lottery identities remain available for preserved history.
- Added lazy-loaded archive reached from the bottom of Home, lottery and jackpot filters, full integer payout amounts, Moscow dates including year, expandable combinations/ticket totals and compact Bingo records without the long number sequence. Gold jackpot cards show both draw number and the recorded jackpot amount. Browser checks use isolated synthetic fixtures; no purchases or production transactions.
- Verification: 303 backend tests passed, one existing Windows symlink skip. New archive query/projection/auth regressions pass. Whole-project Ruff/mypy were attempted: existing violations in migration 0045, telegram_bot and application/dual plus seven pre-existing formatting differences remain outside this change. Mini App typecheck/lint/build and all 112 tests passed (single worker after a parallel lazy-import timeout). Admin: 33 tests; Web: 32 tests; both typecheck/lint/build passed without source changes. Mobile archive smoke at 390×844 and 320×640 verified readable cards, expanded numbers and jackpot filtering. No actual Telegram device was available.
- Publication scope: api and gateway only, preserving the exact production web/admin assets. Shared operations lock covers source/database backup, upload, image assembly, diagnostic archival, restart and health verification.
- Published 1.55.0 (7d26202): local source/release backups, VPS source/assets rollback archive and database dump created; API/bot diagnostics archived before recreation. API healthy, bot/database untouched. Production read-only smoke verified 30 rows, cursor continuity, all 9 lottery filters and 11 jackpot records; Bingo omits sequence/count and Fast is excluded. Public HTTPS serves exact release HTML/version 1.55.0, health 200 and archive unauthenticated 401. Web/admin file-tree hashes before and after publication are identical.

## Unified VPS maintenance and important diagnostic retention — 2026-10-04

- Added one stdlib maintenance entry point with daily 05:00 MSK cleanup and hourly API/bot diagnostic capture. Compact policy for fewer than 50 players: 512 MB build-cache reserve with 48-hour minimum age; current/referenced images plus two tagged rollback versions, seven-day image age; newest three known rollback archives per category plus 14 days; known temporary uploads after 48 hours. Unknown files, dumps, symlinks, hardlinks and all Docker volumes are excluded.
- Financial ledger, balance movements, purchased tickets, draws and database audit history remain permanent. Diagnostic gzip copies are retained for 90 days, with private directories/files and per-container capture cursors. Failed capture aborts cleanup. API/bot Docker buffers use 20 MB × 5; gateway/database use 10 MB × 3. Save available logs before recreation and retain new-container logs hourly. Diagnostics are copies of available buffers, not a replacement for the permanent database ledger.
- Shared publication/maintenance flock and separate backup flock prevent overlap. General release helper now holds the lock throughout, marks rollback images and captures diagnostics before restarting; broad deployment-time pruning was replaced with scheduled maintenance. Existing daily 03:30 MSK database backup and 14-day dump retention remain intact. No business rule, schema, frontend or money changes.
- Verification: focused lint/format, 13 isolated housekeeping regressions (12 passed and one symlink check skipped on Windows; the suite passed on Linux), release CLI dry run, Git whitespace, systemd unit and Compose configuration checks. No purchase tests or transactions. Publication-lock contention correctly skipped cleanup. Local/VPS source backups and a validated PostgreSQL dump preceded installation.
- Production installed and verified: all four existing images and persistent-volume identities are unchanged after bounded-log recreation; all services healthy with zero restarts, public HTTPS health 200 and frontend version 1.54.1 unchanged. Pre-recreation API/bot logs were saved, private gzip archives read back successfully, and both timers enabled. First cleanup removed 14 expired uploads and one old unreferenced image plus eligible build cache, freeing 1,509,617,664 bytes; 26,923,982,848 bytes free and no disk warning. Retention settings and growth/tuning instructions are in docs/SERVER_STORAGE.md and AGENTS.md.

## Product brand spelling and server storage audit — 2026-10-04

- Applied docs/brand.md spelling to visible Mini App, Web and Admin copy, preview labels and bot lottery-name formatting. Added shared response view-data aliases for lottery names, favorites and player notifications; HTTP and Mini App SSE use the same formatter. Stored cart labels are normalized on read. Replaced the previous JSON-wide PLL string substitution with field-specific formatting, preserving usernames, auth tokens, audit reasons, technical codes, numbers and prices. Historical database rows, migrations and prior release notes remain intact.
- Bot changes are infrastructure text formatting only; notifications are formatted from legacy payloads without mutation. No purchase, draw, scheduler, auth or money rule changes. Publication affects gateway and bot only; API and database remain running.
- Verification: all three frontends passed lint and TypeScript/production build; focused checks cover aliases, non-mutation, user/technical data preservation, all three HTTP clients, SSE, stored cart labels, catalog/home/navigation and bot notification labels. Shared formatter lint and focused Python lint/tests passed. Mobile browser smoke at 390×844 confirmed Casper Bingo/Grand in the catalog and Casper Fast in heading/dock/footer with no legacy spelling or horizontal overflow. Actual Telegram device unavailable. No purchase tests or transactions.
- Read-only VPS audit: daily 03:30 MSK database backup with removal of dumps older than 14 days; system temporary-file cleanup active; journald capped at 1 GB. Docker pruning is part of the general release script, with 2 GB build-cache reserve and unused labelled images older than 48 hours. No dedicated Docker cleanup schedule; current container JSON logs have no size/rotation limits. Approximately 25 GB free of 40 GB. Details in docs/SERVER_STORAGE.md; no server maintenance configuration changed.
- Release 1.54.1: gateway and bot only, with local and VPS rollback backups; verify API health, bot runtime formatter, exact public HTML and assets for all three interfaces. 21 focused frontend checks and 13 Python formatting checks passed.

## Mini App: Fast spacing, signal repair and Telegram fullscreen — 2026-10-04

- Removed the Fast eyebrow and reduced header/section gaps. Restored FLASH's 20-cell signal as a bounded 5-column animated grid; the former flex row retained square cells and overflowed its panel. Removed the decorative orbit around device illustrations, retaining Pulse's illustrated pedestal. Added distinct blue, ruby and emerald card/picker surfaces without new image payloads or changes to selection, live timing or purchases.
- Request fullscreen through Telegram SDK 8.0+ on actual Mini App launches, with older/unsupported platform fallback. Shared safe-area variables combine native device and Telegram content insets; shell, navigation and fixed ticket controls consume them. Telegram still owns its close/menu controls. No authentication or business rules changed.
- Verification: 11 focused fullscreen initialization, layout and Fast selection tests passed; no purchase tests or transactions. Frontend lint and TypeScript/production build passed. Browser smoke at 390×844 and 320×640 confirmed no horizontal overflow and all FLASH cells inside the panel. A temporary fixture verified combined top inset 76px and bottom inset 24px; removed after use. Actual Telegram device unavailable.
- Release 1.54.0: miniapp/gateway only, with local/VPS rollback backups and production health, version, exact HTML and changed asset verification.

## Mini App: dimensional Fast devices and tactile selection — 2026-10-04

- Replaced Fast's flat background scenes with three transparent device illustrations, graphite/chrome card surfaces and optical-glass accents. Preserved animated Pulse trace, signal indicators, code indicators, card ordering and reveal transitions. The eager Fast shell now shares its background with the header; no separate dark stripe while the lazy screen loads.
- Added FastArtifact, a decorative image component with CSS float/double-beat motion. Explicit 480×480 dimensions, reduced-motion rules and visibility/offscreen pause; no engine, animation loop or business dependency. Three WebPs total 146,734 bytes and are isolated to the Fast chunk. Prompts/provenance: docs/design/fast-device-assets.md.
- Rebuilt picker presentation as a compact instrument console with large engraved keys, selected glass highlights, separate Pulse fields and a recessed combination display. CODE shows single digits and an accessible backspace label; input keys no longer claim toggle-button semantics. Existing handlers, limits, API calls, prices and number encoding are unchanged.
- Fast live/result cards use the same materials, with flexible rows to prevent overlap around long headings and the Pulse cipher. Server reveal timing, ordering and result values are unchanged. Other lotteries were not restyled.
- Verification: 8 focused selection/CODE keypad/live-display tests passed; 3 purchase tests excluded. Frontend lint and TypeScript/build; local browser preview at 390×844 and 320×640 covering all three pickers, Pulse 11/12 and P1/P6, ordered repeated CODE digits, no horizontal overflow, and action buttons above the fold. A temporary local fixture verified Pulse live and completed 2+2+cipher rendering; removed after use. No ticket purchase tests or transactions. Actual Telegram device unavailable.
- Release 1.53.0: miniapp/gateway only, local and VPS rollback backups, production health/version/HTML and new asset checks.

## Mini App: Casper Bingo emerald ticket edition — 2026-09-28

- Added presentation-only BingoEdition: emerald cardstock, foil frame, medallion, ivory inset and the original server-provided 3×4 row order. Purchased serials, draw/date/price, hits and results retain their existing data. Selection and detail use the new design; live Paper is unchanged.
- Added a native horizontal scroll-snap deck with visible next/previous controls and multi-selection retained across browsing. Selection/disabled rules, inventory loading, favorites, purchase handlers and API contracts are unchanged. Compact-height styling keeps the ticket and deck controls above fixed checkout at 320×640.
- Generated a transparent 490×512 WebP ticket composition (47,876 bytes) for Bingo catalog/header only. Real ticket numbers remain DOM text; all interactive depth uses CSS, with no 3D engine or continuous animation. Prompt and provenance: docs/design/bingo-edition-asset.md.
- Verification: 10 focused Bingo display/selection/filter/dialog and catalog tests passed; 4 purchase-related tests skipped. Miniapp lint and TypeScript/production build; browser preview smoke at 390×844 and 320×640, next/previous, multiple selections, detail and focus restoration. Actual Telegram device unavailable. No purchase tests or transactions performed.
- Release 1.52.0 affects miniapp/gateway only. Local/VPS rollback backups and production health, version, exact HTML and changed assets are required for publication.

## Mini App: unified draw-game ticket screens — 2026-09-28

## Mini App: classic 6/36 ticket and catalog identity — 2026-09-28

- Added ClassicTicket as a presentation-only branch of TicketComposer for khan. Existing selection, limits, randomization, favorites, repeat count and buy handlers remain in the shared composer. Printed circular marks feed a six-ball selection tray; accessible ball buttons remove a selection through the same toggle. In-flight requests lock both marks and balls.
- Added ClassicHeader only for khan ticket mode. Live mode still uses the unchanged GameHeader and LiveView. The compact brass-drum composition and navy/ivory catalog design are scoped to 6/36; Fast and other lottery rooms are untouched.
- Paper, perforation, ink and enamel-ball depth are CSS effects on real accessible controls. Drum is a generated transparent WebP, not a runtime 3D scene. Source/prompt documented in docs/design/classic-drum-asset.md; no engine or animation loop added.
- Verification: 12 focused selection/catalog/App checks passed without invoking purchase handlers, plus frontend lint and TypeScript/build. Browser smoke with preview data at 390×844 and 320×640: selection/removal, full field, quick choices above checkout, no horizontal overflow. Actual Telegram device unavailable. No ticket purchase tests or transactions performed.
- Release 1.51.0 affects miniapp/gateway only; retain local/VPS rollback backups and verify production health, version, HTML and new assets.

## Mini App: dark home and compact glass navigation — 2026-09-28

- Rebuilt Today with a compact server-driven next-draw card, permanent ticket/catalog shortcuts, personal upcoming draw, dated Moscow schedule, optional latest jackpot and collapsed platform statistics. Live/result navigation and the separation of regular games from Fast are preserved. Removed the scrolling statistics strip and poster layout. Shared discovery styles remain eager because the Fast footer depends on them.
- Added a generated 512×362 transparent orbit illustration (23,422 bytes), reusing the approved ticket asset for personal navigation. Built-in image generation; prompt stored in docs/design/home-orbit-asset.md. No WebGL engine or continuous animation. Server data and countdown render independently of image decoding.
- Reduced the dock from a 78px porcelain panel to a 54px dark glass capsule, at most 300px wide, retaining 44px touch targets, readable text labels, focus states and unread indication. Opaque fallback when backdrop blur is unavailable or reduced transparency requested. Changed the account ticket card and ticket tabs to navy.
- Verification: focused home/empty/participation/live/result/date and account/navigation tests; miniapp lint, typecheck/build; browser smoke at 320×640 and 390×844. No purchase tests or transactions. Actual Telegram device checks unavailable; browser viewport checks are recorded separately.
- Release 1.50.0: miniapp/gateway only, with local/VPS rollback backups and production version, HTML, asset and health verification.

## Mini App: personal dashboard and dimensional navigation — 2026-09-28

- Extracted the personal overview into a lazy AccountHub chunk. Replaced repeated account tabs and header balance with a compact account heading, single balance card, active-ticket action, history/catalog shortcuts and expandable statistics/settings. Existing server values, ticket filters, notification preferences and purchase flows are preserved.
- Added a 29,220-byte transparent WebP illustration through built-in image generation, and lightweight layered SVG icons. The artwork loads only with the account screen; dimensions reserve its space. No 3D runtime or animation engine was added.
- Replaced old bottom navigation markup with an isolated porcelain dock, accessible selected-page state, unread dot, keyboard focus, reduced-motion support and 64px-tall targets. Reselecting My returns to its overview and scrolls to the top. Fast gameplay and lottery rooms are unchanged.
- Verification: focused account/navigation/history UI checks, miniapp lint and TypeScript/production build; browser smoke at 320×640 and 390×844 with preview data. No purchase tests or transactions. Actual Telegram device verification was unavailable; browser viewport smoke does not replace that check.
- Release 1.49.0 affects miniapp/gateway only; local/VPS rollback archives and production health/version/HTML/asset verification required.

- Replaced regular room mastheads with a shared compact GameHeader. Isolated TicketComposer styling replaces accumulated picker theme overrides: no oversized instructions, grave-shaped controls, duplicate random actions or cart-add step. Direct purchase callbacks, server formats, field offsets and repeat semantics are retained. Existing saved carts remain accessible.
- Light ticket surfaces share spacing, typography and interaction states, with separate game accents/artwork. Grand and Casper Ball preserve independent fields; Dual keeps 2+2 with no repeats/favorites. New regular selection code is lazy-loaded. Fast and draw execution are unchanged.
- Bingo now places its pool tickets directly below the compact header/quick actions. Optional sets/search are collapsed below tickets; detail inspection, selected-ticket removal, mine/live views and retry handling remain available. Checkout stays visible. Updated the local Casper Ball preview to the existing server 5/36 + 1/8 format.
- Added room-entry scroll reset and regular-room feedback rendering. UI verification covers number limits and field independence, in-flight control locking, Bingo selection/details/search, room navigation and mobile layouts. Purchase tests and transactions are deliberately excluded. Frontend lint, typecheck and production build are required for this release.
- Release 1.48.0: only miniapp/gateway, with rollback archives and production version/HTML/health/asset verification.

## Mini App: illustrated lottery catalog — 2026-09-28

- Replaced the cramped two-column thumbnails with full-width scene compositions, consistent price/schedule placement and a single open affordance. Existing lightweight scene assets are reused, with eager loading only for the first visible card and lazy loading below. Bingo uses the existing club scene instead of an oversized brand mark.
- Catalog styles/component are isolated from Today, lottery rooms and Fast. Server names, jackpots, ticket prices and daily/weekly filters are preserved; instant LIVE has a compact entry after draw games.
- Verification: focused catalog filtering/navigation and App entry checks; frontend lint, TypeScript and production build; mobile browser visual smoke at 320/390 px. No purchase tests or transactions.
- Release 1.47.10: miniapp-only gateway deployment with local/VPS rollback backups and public version/HTML/health verification.

## Mini App: первый экран до загрузки React — 2026-09-28

- Существующие утверждённые PNG уменьшены для реальных размеров показа внутри miniapp: знак шапки 18,5 КБ вместо 935 КБ, отдельный знак сцены 55 КБ, горизонтальный логотип 38 КБ вместо 627 КБ, favicon 6 КБ вместо 1,38 МБ. Мастер-файлы в shared не изменены. Версии производных файлов закреплены в URL.
- В HTML добавлена стартовая оболочка и responsive preload знака. Она видна до выполнения JS и остаётся геометрически согласованной с React-skeleton и шапкой. Главная теперь ожидает только dashboard; account загружается параллельно.
- Проверки: 5 точечных тестов загрузки/главной, lint изменённого TypeScript, typecheck+production build, визуальный smoke на 320 и 390 px в локальном design preview; покупки не запускались.
- Публикация: только miniapp в gateway, с резервной копией и production health.

## Mini App: preview sizing and personal area — 2026-09-28

- Исправлена несовместимость picture/source (мобильный знак) с шириной 138px: контейнер и картинка теперь ограничены высотой шапки, мобильная ширина 42px. Масштаб каталога и главного постера выровнен отдельно от комнат лотерей.
- Перестроена иерархия «Моё»: баланс, крупные строки действий, ближайшее участие, подробности в доступных native details. Исправлены маршрутизация пустого состояния и наследование фильтра Fast. Смещение любимых специальных чисел берётся из метаданных лотереи.
- FastPicker показывает ошибку непосредственно в форме и блокирует изменение комбинации при ожидающем запросе. Quick-buy не позволяет открыть picker во время пакетного запроса. Генерация пакетов просмотрена статически; причина серверных сбоев пакетной покупки не подтверждена без операций покупки.
- По просьбе владельца не запускались покупки, тесты покупок и backend-suite. Точечные UI-проверки: 8 тестов выбора Pulse, сообщений/блокировки формы и переходов/фильтров «Моё»; typecheck, lint, production build и мобильный визуальный smoke.
- Публикация: только miniapp assets в gateway с сохранением существующих сборок admin/web, резервной копией и проверкой production health.

# Development log

## Block A owner policy and provisional copy — 2026-10-05

- Recorded owner-approved automatic/editorial categories, milestone approach, no-personal-information rule, same-draw grouping, artwork selection, missed-event handling, 24h Story intent and final hashtag preference. Scheduling, counter scope and Story destination ambiguities remain open; no conditions invented or delivery enabled.
- Prepared an isolated editorial folder with 30 provisional Story title/channel copy variants for automatic A1/A4 and an interactive seen/unseen Story preview. Owner subsequently confirms Mini App 24h scope and persistent channel posts, and replaces once-daily scheduling with three daily scans plus immediate sending; scan hours remain pending. Text-bank structure validated and focused 390px browser smoke confirms viewed cards are muted/moved last with no horizontal overflow. This is documentation/design preparation, not a product release; production and channel unchanged.

## Atmospheric September publication collection — 2026-10-05

- Added ten owner-supplied autumn landscape scenes for september, each in 9:16 Stories and 4:3 posts. Retained full portrait imagery, strengthened lower copy contrast for bright landscapes, reused the manual editor and game-specific CTA. All previous 1046 catalog entries compare equal; 320 new event references share 20 background files per client. No automation or domain/schema changes.
- Owner requested minimal relevant verification and explicitly authorized one marked test photo post to @casper_loto. Check only catalog preservation, image dimensions, affected frontend lint/typecheck/build, focused editor/export smoke and production health/assets. Persistent channel delivery remains disabled.
- Verification completed: 20 correctly sized identical client backgrounds (4.16 MiB/client), previous 1046 entries preserved, one focused catalog test and affected frontend lint/typecheck/build passed. Editor selected all ten designs and initiated PNG export; the browser closed before saving the download, so the inspected test PNG was rendered with the exact shared production text-layout function. No broad frontend/backend suite rerun for this asset-only addition.
- Published 6d96da0 using a 29.82 MiB overlay archive: source/assets and database backups, rollback images and diagnostic archives preserved under the shared operations lock; existing immutable asset files retained. Production catalog has 1366 entries and no player publications. HTTPS checks passed for paired new samples and a legacy sample on both hosts; API/database health is OK. Corrected a direct Vite build's `development` version marker with a gateway-only 2.27 MiB follow-up; public Mini App version 1.58.2, HTML and entry JS match the corrected build. API 1.48.2 / Admin 1.55.2; bot/database were not recreated.
- Exactly one owner-authorized test photo with caption/hashtags was delivered by the existing bot: https://t.me/casper_loto/4 (message_id 4). Delivery receipt retained locally to prevent accidental resend; owner will delete the post. No permanent channel sending or automatic event policies enabled.

## Owner artwork for 6/36 publications — 2026-10-05

- Added nine owner-supplied navy/gold/ivory scenes exclusively for khan: light trails, six pedestals, ticket, six orbits, cosmos, ball cabinet, arc, stage and one drum. Paired 1080×1920 Stories retain portrait scenes and reserve lower copy; 1200×900 posts use the same scene beside a separate text column. Approved symbol and game label are composited during deterministic SVG/raster compilation; no generated replacement art or embedded event facts.
- Preserved all 758 original catalog snapshots exactly. Added 288 editorial references (nine choices × existing 32 labels) sharing only 18 versioned backgrounds per client. Five text zones remain editable through the existing Admin/ Mini App renderer; game-bound CTA and manual publication workflow are reused. Sources, provenance, paired overview and reproducible incremental compiler are tracked separately from the historical local design gallery.
- Current product scope is Admin + Mini App. No scheduler, automatic conditions, expiry, channel messages or B/C/D implementation. OD-037 records the remaining block A policy questions and the source README provides a reusable visual brief.
- Verification: all 758 old catalog entries compare equal to the previous release; nine × 32 unique khan entries reference exactly 18 correctly sized WebPs, about 1.99 MiB per client. Backend 316 tests passed with the existing Windows symlink skip; Admin 35 and Mini App 118 tests passed, both lint/typechecks passed. Vitest required elevated esbuild directory access on Windows. Admin browser smoke selected all nine pairs, checked asset loads, exported a real 1200×900 PNG with editable text and confirmed no overflow at 390 px. Mini App smoke uses synthetic publications only; no example is published to production.
- Published 7ca3475: Mini App 1.58.1 / Admin 1.55.1 / API 1.48.1. All frontend builds passed; source/database/rollback backups and API/bot diagnostic archives were preserved under the shared VPS operations lock. Only API and gateway recreated. Production serves 1046 catalog entries and zero publication rows; API/database health is OK and migration 0048 remains head. All 18 new backgrounds plus a legacy sample match local SHA-256 over public HTTPS on both hosts, HTML matches builds and version is correct. An initial transient TLS reset passed bounded retry. Channel delivery remains disabled; runtime directories allocate 77 MiB per client and VPS has 23 GiB free. Mobile smoke checked all nine Stories, no horizontal overflow and CTA navigation into the khan game room.

## Mini App: static cache and screen chunks — 2026-09-28

- Caddy отдаёт `/assets/*` и версионированные `/brand/*` с годовым immutable-кешем. HTML остаётся `no-cache`, API по-прежнему `no-store`: баланс, статусы продаж и результаты не берутся из кеша браузера.
- Today отделён от Discovery; Discovery, FastView, BingoView и KasperLiveView загружаются лениво с видимым placeholder при первом переходе. Стартовый JS в production build уменьшился с 154,36 до 137,97 КБ gzip.
- Добавлены browser performance marks для HTML-оболочки, исполнения клиента, получения dashboard и первого отображения главного экрана. Проверены только переходы и загрузка экранов; покупки не выполнялись.

## Mini App: first-load and rendering budget — 2026-09-25

- Убран одновременный запрос двух вариантов логотипа в шапке через responsive `picture`.
- Сцены каталога теперь загружаются лениво, а стартовые `hero`-сцены используют один raster-слой и не запускают декоративную анимацию; эфир и picker сохраняют многослойную анимацию.
- Проверки: Mini App typecheck, ESLint, 74 Vitest-теста и production build.

## Kasper Bingo: второй ежедневный слот — 2026-09-25

- Добавлен утренний тираж Kasper Bingo в 10:30 МСК; вечерний слот 22:00 сохранён.
- Расписание обновляется миграцией `0047_bingo_second_daily_slot`; новые будущие тиражи и их пулы создаются штатным scheduler/recovery-путём.
- Добавлен regression-тест перехода между слотами 10:30 и 22:00.

## Admin owner dashboard focus pass — 2026-09-25

- Боковая панель админки теперь прокручивается целиком; фиксированный список больше не обрезает нижние вкладки на коротких экранах.
- Дневная история использует существующий `/admin/activity` и показывает пять последних московских дней без изменения исторических данных или схемы.
- Выдача interesting facts ограничена 50, а одинаковые по лотерее, типу и заголовку кандидаты схлопываются после сортировки по дате и score.
- Проверки: backend admin/facts — 27 тестов, admin frontend — typecheck, lint, build и 33 Vitest-теста.

## Auto-play allowlist and restoration — 2026-09-25

- По решению владельца Casper Dual исключена из автопокупки на уровне списка разрешённых лотерей и проверяется повторно в сервисе покупки; общая настройка игрока в админке не может обойти запрет. В админке показано понятное ограничение.
- Для прежних лотерей кандидаты выбираются только из первых пяти открытых тиражей каждой лотереи. Сервис покупки повторно проверяет окно и требует явного выбранного тиража для AUTO_PLAY, поэтому один запрос автопокупки не может создать новый тираж. Новые продукты по умолчанию отсутствуют в allowlist.
- Порядок безопасного возврата: сначала публикация и проверка запрета Dual на production, затем включение семи ранее временно отключённых настроек игроков по сохранённым значениям (5 случайных билетов на тираж) через аудируемый админский сервис. Dual-билеты и ledger не меняются.
- По просьбе владельца проверки ограничены затронутыми backend-тестами (69 пройдены), Ruff/mypy для изменённого backend и typecheck/lint/build админки. Сборка Vite потребовала запуска вне filesystem sandbox для доступа к vite.config.ts.

## Casper Dual auto-play incident — 2026-09-25

- Предыдущая проверка публичной нумерации была неполной: рост номеров вызван цепной автопокупкой, а не множеством независимых игроков. AutoPlayService выбирал все открытые тиражи Dual, а покупка в последнем созданном тираже подготавливала следующий раунд, который сразу попадал в очередной запуск автопокупки.
- На production штатной административной операцией с аудитом временно выключены семь настроек автопокупки. В 00:31 МСК зафиксировано 6 511 билетов Dual (6 510 AUTO_PLAY и один MANUAL); последняя покупка была в 00:27:52 МСК. Купленные билеты, списания и тиражи сохранены по просьбе владельца, без удаления и переписывания ledger.
- AutoPlayService и сервис покупки по выбранному тиражу теперь ограничивают начало билета первыми четырьмя из пяти ближайших открытых тиражей Dual: второй раунд всегда остаётся в окне. Это исключает саморасширение горизонта автопокупки и прямой обход ограничения. Настройки игроков остаются выключенными до отдельного решения о возобновлении.
- Проверки: 271 backend-тест пройден, включая регрессии окна Dual в автопокупке и прямой покупке; изменённые файлы проходят Ruff lint/format и mypy. Общий Ruff/mypy отмечает существующие ошибки в других файлах; frontend typecheck/lint проходят, Vitest в sandbox не смог открыть Vite config (Access denied). Frontend в этом релизе не менялся.

## Mini App 6/36 depth pass — 2026-09-24

- По визуальной проверке верхний hero-блок уменьшен примерно вдвое: лототрон стал приглушённым фоном, а стеклянная карточка оставляет только джекпот и количество билетов.
- Убрана вложенная рамка вокруг джекпота, стоимость комбинации удалена из верхней части выбора, а избранные комбинации перемещены непосредственно под поле чисел.
- Исправлена ошибка предыдущего прохода: визуальный слой комнаты 6 из 36 больше не скрывается. Существующая сцена лототрона возвращена в hero-блок и дополнена 2.5D-слоями, стеклом, бликами, градиентной глубиной и объёмными шарами поля.
- Интервал показа шаров 6 из 36 увеличен с 3,2 до 4,7 секунды в серверной presentation timeline; призовые и правила тиража не менялись.
- Минимальные проверки для этой правки: frontend typecheck/lint/build и точечный backend-тест timeline.

## Mini App 6/36 visual pass — 2026-09-24

- Сделан быстрый вход в комнату лотереи: уже загруженная карточка открывается сразу, а актуальный дашборд и избранные обновляются в фоне.
- Для 6 из 36 убран тяжёлый механический лототрон и анимация сцены в эфире. Оставлен лёгкий статичный экран с текущим шаром, прогрессом и шестью слотами результата.
- В комнате 6 из 36 верхний блок с повторяющимся названием заменён на компактный джекпот; избранные комбинации подняты сразу под итог выбора.
- Проверки: Mini App `tsc -b` и ESLint проходят. Vitest не запустился из-за ограничения доступа встроенного esbuild к `vite.config.ts`; бизнес- и backend-проверки не запускались, так как изменения только в UI.

## Casper Ball PSS transition — 2026-09-24

- Добавлен ruleset `casper_ball_5_36_1_8`: пять основных чисел 1–36 и один
  Casper Ball 1–8, с выплатами 50M / 10M / 1M / 100K / 12K CAS.
- Миграция `0043_pss_casper_ball` возвращает только купленные билеты будущих
  PSS-тиражей, создаёт компенсирующие ledger-записи и устанавливает новый
  стартовый джекпот. Завершённые тиражи и публичные номера не изменяются.
- Текущая аналитика исключает старые PSS ruleset, а web-эфир и карточки
  показывают название Casper Ball и отдельное специальное поле.

## Phaser «6 из 36» local visual stand - 2026-09-24

- Изучены действующая Phaser-архитектура «ГРОБ», визуальная концепция, bridge,
  purchase flow и серверный формат `classic_6_36`; backend, игровая математика,
  Telegram Mini App и остальные лотереи не менялись.
- Добавлена отдельная lazy-loaded Phaser 3 сцена `khan`: пустой стеклянный
  лототрон в синей вечерней студии, 36 объёмных интерактивных шаров, шесть
  физических гнёзд билета, дуговая анимация установки, световые слои и
  фактический Casper Loto wordmark из shared brand assets.
- После визуального ревью плоский пюпитр заменён единым перспективным 2.5D-
  терминалом по референсу владельца: большой стол, шесть физических верхних
  гнёзд и отдельный правый планшет имеют общий золотой корпус. Геометрия вынесена
  в изолированный `ClassicLotteryConsole`, чтобы позднее переиспользовать форму
  с другими наборами чисел без копирования сцены.
- Джекпот перенесён с верхнего HUD на динамический приборный экран между столом
  и билетом. Логотип установлен на контрастную navy-табличку, баланс получил
  короткий двухстрочный корпус под значение до `9 999 999 999 CAS`, а шары —
  процедурные объёмные текстуры вместо плоских Phaser-кругов.
- Ручная покупка и быстрые случайные покупки x1/x5/x25 используют существующий
  `/lotteries/khan/purchases`, server preflight, один атомарный request,
  idempotency key, single-flight guard и восстановление неоднозначной покупки.
- Для согласования оставлен локальный стенд `/web/khan-preview.html`, который
  не требует API и имитирует только визуальные состояния. Проверены desktop и
  portrait 390×844, выбор шести шаров, ready-state и pending-покупка.
- По уточнению владельца эфир «6 из 36» не реализовывался; общая вкладка
  «Эфир» и существующие live-контракты не изменялись. Production deployment не
  выполнялся.
- Проверки: web typecheck и lint прошли; 32 frontend-теста прошли; production
  build прошёл с существующим предупреждением Vite о размере lazy Phaser chunk.

## Casper Loto brand foundation - 2026-09-24

- Зафиксированы утверждённые название Casper Loto, направление C-монограммы со
  сферой, основная navy/ivory/gold палитра, secondary cyan, правила слогана и
  запреты в `docs/brand.md`.
- Принят финальный production asset pack: исходные PNG без перерисовки,
  ресайза, фильтров или перекраски размещены в
  `frontend/shared/assets/brand/`, а их роли закреплены в manifest.
- Gold/ivory wordmark и C-symbol подключены к Web, Telegram Mini App, панели
  владельца, favicon и app icon; старые K-SVG удалены. Cyan сохранён только как
  неподключённый secondary digital accent.
- Активные пользовательские подписи приведены к `Casper Loto`. Технические
  идентификаторы, исторические записи, игровые механики, Phaser-сцены и
  lottery-specific палитры не изменялись.
- Проверены lint и production build для Web, Mini App и Admin, 27 целевых
  тестов Mini App и 25 backend-тестов пользовательских сообщений/метаданных;
  все проверки прошли. Web сохранил существующее предупреждение Vite о размере
  lazy Phaser chunk.

## Phaser «ГРОБ» vertical slice - 2026-09-23

- Replaced the previous web-only React/CSS GROБ screen with a dynamically imported Phaser 3 experience; catalog/login/other lotteries keep the existing initial bundle and behavior.
- Added an instance-scoped typed bridge, application controller, unbiased Web Crypto quick-ticket generation, persisted purchase attempts, single-flight protection, and server-time live phase derivation.
- Built a layered crypt scene with an optimized WebP matte, production sarcophagus and seal sprites, two readable 8+8 number arcs, physical socket placement, ambient dust, responsive staging, keyboard/screen-reader mirrors, and reduced-motion behavior.
- Added the dedicated grob-only live scene and verified the manual cycle, automatic empty draft, x1/x5/x25, desktop, 390×844 portrait, and a clean browser console against a local mocked API fixture; the fixture was removed after QA.
- Backend, lottery mathematics, ledger, migrations, and Telegram Mini App were not changed.
- Final owner review replaced the detached lever with the existing central lid seal as the manual-purchase control, strengthened its ready-state glow, grounded the sarcophagus, and moved the live draw number onto the machine while removing ticket metadata from the broadcast.
- Release version: web 1.46.0. The localhost-only review entry and fixture were removed before publication.

## Design documentation - 2026-09-23

- Зафиксирована эталонная визуальная и UX-концепция веб-версии «ГРОБ»: единая 2D/2.5D-сцена с саркофагом-машиной, физическим выбором 3 из 16, мгновенными покупками, отдельной режиссурой эфира, требованиями к доступности и производительности.
- Production-код и действующая механика лотереи не изменялись.

## [1.45.1] - 2026-09-23

- Added `/admin/jackpots` paging over immutable jackpot-win events and `period=archived` to completed-draw search for inactive lotteries or draws whose ruleset snapshot differs from the current ruleset.
- Added the owner-side jackpot catalog and historical-format archive; each item opens the existing immutable draw detail view.
- Made the Fast control room surface jackpot history directly, defaulted system navigation to event logs, and moved lottery balances below primary service diagnostics.

## [1.45.0] - 2026-09-23

- Extended admin player search results to 500 entries, made internal UUIDs visible/copyable, and routed global ledger player IDs to their dossiers.
- Added a unified paginated player ticket query spanning draw tickets and instant tickets plus all-time per-lottery totals; added filters and unbounded page-through to both ticket and CAS histories.
- Counted instant tickets in the player's all-time ticket total while keeping them out of active-ticket counts.

## [1.44.0] - 2026-09-23

- Replaced the GROБ modal presentation in web with a dedicated responsive game scene, custom environment artwork, numbered tombstone controls, and reduced-motion fallbacks.
- Routed the existing purchase interaction to the unchanged server purchase endpoint; only web presentation changed.

## [1.42.5] - 2026-09-23

- Reorganized the account overview around the player's immediate questions instead of profile details.
- Kept detailed history, favorites, and notification settings available below the primary hub actions.

## [1.42.4] - 2026-09-23

- Consolidated ordinary-lottery Mini App purchase actions around the shared number picker.
- Kept random purchases confirmation-free, preserved the cart for users building multiple manual tickets, and kept five-draw participation explicit.

## [1.42.3] - 2026-09-23

- Reviewed the Mini App at mobile widths and tightened responsive sizing for shared screens and Kasper LIVE.
- Kept the changes presentation-only; purchase, prize generation, history, and ledger flows were not altered.

## [1.42.2] - 2026-09-23

- История из обзора аккаунта теперь сразу загружает общий список игр, включая Kasper LIVE.

## [1.42.1] - 2026-09-23

- История Mini App объединяет завершённые Kasper LIVE билеты с обычными билетами при выборе «Все игры»; отдельный фильтр позволяет открыть только мгновенные билеты.
- Символьная комбинация Kasper LIVE теперь кодирует категорию: проигрыш — три разных символа, выигрыш — три одинаковых символа, выбранных для суммы приза.
- Проверены backend-правила символов и Mini App typecheck/lint/72 tests.

## [1.42.0] - 2026-09-22

- Добавлена независимая от тиражей модель `instant_tickets` и миграция `0042_kasper_live`; завершённые мгновенные билеты неизменяемы, имеют собственный сквозной номер, версию таблицы шансов и сохранённую визуальную комбинацию.
- `InstantTicketPurchaseService` атомарно и идемпотентно покупает только 1 или 3 билета. Стоимость списывается с пользовательского баланса и сгорает; ненулевой приз проводится отдельными ledger-движениями из Фонда Каспера пользователю. Блокировки берутся в едином порядке `fund -> balance`.
- Mini App получил отдельный Kasper LIVE без изменений Web: сервер отвечает готовым результатом, клиент показывает общий 2,5-секундный выпуск и блокирует повторное нажатие до раскрытия. Последние мгновенные билеты доступны на том же экране.
- Admin получил отдельный read-only раздел только с четырьмя агрегатами без привязки к игрокам.
- Проверены граничные значения всех призовых категорий, RTP 60,5%, пакет из трёх билетов, сжигание цены и парные проводки выигрыша. Полный backend: Ruff, mypy и 242 теста; Mini App: lint, typecheck, 72 теста и production build; Admin: lint, typecheck, 27 тестов и production build.
- Локальный мобильный preview проверен на размере 390×844. Computer Use не предоставил браузерную поверхность; headless Chrome и DOM-снимок подтвердили экран, историю и отсутствие выхода контента за ширину после исправления компактного баланса.

## Documentation - 2026-09-22

- Добавлен единый актуальный справочник `docs/LOTTERIES.md` по десяти активным production-лотереям; README больше не содержит неполный устаревший список.

## [1.41.1] - 2026-09-22

- Owner dashboard загружает `standard` scope для рабочих карточек и отдельный дешёвый `all` snapshot только для общей денежной и тиражной сводки. Fast больше не смешивается с показателями джекпотов обычных лотерей.
- Admin v1.41.1 опубликован через gateway после backup; production health-check прошёл.

## [1.41.0] - 2026-09-22

- Добавлены неизменяемые стратегии `fast_5_20_jackpot_only`, `pulse_2_12_2_6_cipher_199` и `code_5_digits`; прежние стратегии сохранены для расчёта существующих тиражей.
- Шифр PULSE генерируется сервером отдельно для сохраняемого билета. Он хранится в выделенном диапазоне массива чисел, без новой таблицы и постоянных дополнительных запросов.
- Миграция `0041_fast_prize_formats` сохраняет snapshots уже запланированных раундов и включает новые правила только для будущих. Оперативная Fast-статистика фильтруется по текущему ruleset, исторические записи не изменяются.
- Критические регрессии покрывают единственную категорию FLASH, обе категории PULSE, обе категории CODE, серверное назначение шифра и совместимость старых форматов.
- Production-выпуск выполнен с предварительным backup и проверкой его структуры; API, bot и gateway обновлены, health-check прошёл, а production-БД подтверждает миграцию `0041_fast_prize_formats` и все три новых ruleset.

## [1.40.0] - 2026-09-21

- Оперативная сводка расширена read-only группировкой сегодняшних покупок и начисленных выигрышей по лотереям в границах суток `Europe/Moscow`; итог остаётся прозрачной формулой `sales - payout`.
- Деталь тиража теперь присоединяет владельца каждого билета и проверяет точную принадлежность к джекпот-категории по неизменяемой проводке `JACKPOT_PAYOUT`. Это устраняет догадки по размеру приза и не меняет историю.
- Список игроков ограничен 200 последними записями и получил серверный поиск с лимитом по имени, username, Telegram ID и UUID. Клиент использует задержку 250 мс и master-detail представление.
- Единая лента событий строится из уже существующих неизменяемых источников: ledger, admin audit, notification outbox и последних тиражей. Новая таблица и миграция не требуются.
- Интерфейс фактов сортирует выборку по score, но вместо технического score показывает владельцу приоритет и человекочитаемые метрики; в буфер попадает только готовая публикационная копия.
- Доверенный браузер реализован долгоживущей подписанной HttpOnly/Secure/SameSite-сессией, а не открытием admin API. Признак `remembered` входит в подписанный payload; `/auth/session` выполняет безопасное скользящее продление и выдаёт новый CSRF. Старые сессии остаются короткими и совместимыми.
- Добавлены регрессии данных владельца джекпот-билета, дневной финансовой сводки и доверенной сессии. Полный `scripts/check.ps1` пройден: Ruff, format, mypy; 224 backend, 71 Mini App, 26 admin и 18 web тестов; typecheck, lint и production build всех трёх frontend успешны.
- Production: `7e62a95` опубликован через `release_vps.py --services api gateway` после успешного backup. Миграций схемы нет; API и база healthy, бот не перезапускался. Публичные admin HTML/JS/CSS отвечают 200 и содержат новый дневной итог, победителя джекпота и доверенный вход. Авторизованный smoke подтвердил v1.40.0, наличие `by_lottery`, серверный поиск игроков, флаг `remembered`, скользящее продление и cookie `Max-Age=7776000`; тестовая HTTP-сессия была эфемерной и не сохранялась на диске.

## [1.39.1] - 2026-09-21

- Playwright MCP подтверждён реальным входом владельца и исходными desktop/mobile скриншотами production Fast. Редизайн начат только после подтверждения доступа.
- FastBroadcast перенесён внутрь station-scene; idle, prelive, starting, revealing и result не создают дополнительного блока под покупкой. Ручной выбор использует ту же сцену, не теряет комбинацию при эфире. Фоновый арт из 1.39.0 раскрыт крупно; отдельные визуальные обработки чисел и motion для каждой игры. Нет новых bitmap assets и заимствований из Mini App.
- Для фазовой визуальной проверки использован отдельный localhost preview с перехваченными API-ответами и тестовым пользователем. Все не-GET запросы preview блокируются; production-покупки не выполнялись, реальные credentials в fixtures не переносились.
- Playwright проверил пять фаз на ширинах 1440/1024/390/360: координаты покупки и высоты каждой секции неизменны между фазами, горизонтального overflow нет. Просмотрены скриншоты desktop, мобильного эфира и ручного PULSE. Дополнительно проверен компактный 1366×768: все три кнопки покупки видны без прокрутки. Артефакты локально в `archive/local/2026-10-20/browser-checks/` и не входят в релиз.
- Добавлены регрессии вложенности эфира, сохранения DOM-сцены и ручных чисел после эфира. Релиз web-only: версия API остаётся 1.39.0, backend и база не изменены.
- Проверки: Ruff, format, mypy; 224 backend, 71 Mini App, 25 admin и 18 web тестов; lint/typecheck/build всех frontend. Общий запуск остановился на существующем нестабильном admin-тесте Escape (`amount=null`); ошибка повторилась в полном admin-наборе, изолированные два случая и последующий полный admin-набор прошли без изменений кода. Остальные шаги после остановки выполнены отдельно. Web console без ошибок, reduced-motion отключает анимацию.
- Production: `46d9182` опубликован через `release_vps.py --services gateway` после успешного backup. API/бот не перезапускались, API/DB healthy, публичный `/health` — 200. JS/CSS побайтово совпадают со сборкой. После публикации просмотрены production-скриншоты 1366×768 и 390×844: три встроенных эфира, ноль нижних панелей, без horizontal overflow и ошибок console. Локальный preview закрыт; реальных покупок в ходе проверки не было.

## [1.39.0] - 2026-09-21

- Fast web вынесен в отдельный компонент с тремя стабильными колонками и локальными live-потоками. Покупка случайного билета — один существующий API-запрос; ручной выбор раскрывается без модального перехода. Проверяются текущий тираж/цена, баланс и закрытие продаж; неопределённая покупка сохраняется в sessionStorage по UUID игрока и игре, повтор использует тот же ключ/числа. Смена тиража или цены блокирует автоматическую новую покупку до проверки пользователем.
- Новая графика создана встроенным imagegen: отдельные FLASH, CODE, PULSE; production JPEG всего около 503 KB. Промпты и происхождение: `archive/reference/legacy-web/archive/reference/legacy-web/docs/FAST_WEB_ART.md`. Старые Fast-сцена и общий крупный SVG-пульс web удалены; остальные экраны не редизайнились.
- Эфир использует существующий `lottery_code` фильтр, опрашивается раз в три секунды, не перекрывает незавершённые запросы, не опрашивается в скрытой вкладке. Числа и призы скрыты до серверных этапов; удержание результата шесть секунд, prelive восемь секунд, как в Mini App. Устаревший поток показывает переподключение. CSS-анимации отключаются вручную и через reduced-motion.
- Read-only live-модель дополнена `primary_numbers_to_pick` и `secondary_storage_offset` из snapshot правил тиража, с fallback на действующий ruleset для старых записей без snapshot. Нет изменений схемы, ledger, scheduler или правил розыгрыша.
- Подключённый браузер снова недоступен (`apps: [], browsers: []`), поэтому визуальная браузерная приёмка не заявляется. Арт-сцены просмотрены непосредственно после генерации.
- Полный `scripts/check.ps1` пройден: 224 backend + 71 Mini App + 25 admin + 16 web = 336 тестов; Ruff, mypy, lint/typecheck/build всех frontend успешны. Новые регрессии покрывают snapshot PULSE, случайную/ручную покупку, CODE с нулём и повторами, повтор после потери связи/перезагрузки, закрытие продаж, смену тиража, синхронизацию раскрытия и устаревший эфир.
- Production: `1818a58` опубликован через `release_vps.py --services api gateway` после backup; бот не перезапускался. Alembic check и проверка backup прошли, API/DB healthy. Публичные HTML/JS/CSS и три изображения — HTTP 200, опубликованные байты совпадают с локальной сборкой. Read-only транзакция проверила реальные отдельные live-feed FLASH/CODE/PULSE и метаданные формата (3/0, 4/0, 2/12); тестовых игроков или покупок на production не создавали. Визуальный browser smoke остаётся недоступен.

## [1.38.0] - 2026-09-21

- Web получил самостоятельную композицию: вход с фоновой сценой, горизонтальная навигация, коллекция игровых миров, Fast-инструмент с SVG-пульсом, адаптивный кабинет и билеты. Использованы существующие фирменные assets; Mini App UI не изменён.
- Новый `WebIdentityService` использует существующие `users`, `web_accounts`, `web_login_tokens`. Telegram-код хранится только как SHA-256, действует пять минут, новый код отзывает прежние; погашение защищено блокировкой строки. Схема не менялась, миграция не нужна.
- Telegram web-сессия привязана к существующему UUID без создания второго баланса. Добавление пароля сохраняет UUID. Регистрация вынесена из API в application service; добавлены ограничения частоты auth-запросов.
- Правила игр, scheduler, расчёты тиражей и ledger не изменялись. Автоматического объединения разных существующих профилей нет.
- Проверки: полный `scripts/check.ps1` пройден — 222 backend, 71 Mini App, 25 admin и 4 web теста; lint/typecheck/build всех frontend и Ruff/mypy успешны. PostgreSQL smoke на отдельной временной базе подтвердил однократное конкурентное погашение кода, общий UUID/баланс и отсутствие повторного welcome grant; временная база удалена. Production-зависимости web: npm audit — 0 уязвимостей.
- Визуальная проверка через подключённый браузер недоступна: инструмент вернул пустой список браузеров. Внешний вид требует отдельной браузерной приёмки.
- Production: релиз `0485307` опубликован через `release_vps.py --services api bot gateway` после резервного копирования; архив базы проверен `pg_restore --list`, Alembic check без расхождений. API/DB healthy, bot/gateway запущены; публичные `/health`, `/web/`, JS/CSS — HTTP 200, неавторизованная сессия и неверный Telegram-код — HTTP 401. Полный пользовательский вход через реальный Telegram и браузер не проверен.


## [1.37.0] - 2026-09-21

### Более редкие джекпоты Kasper Fast

- Добавлены стратегии `fast_3_20` и `pulse_2_12_2_6`; прежние `fast_3_16` и `pulse_2_10_2_5` сохранены в реестре для расчёта уже созданных тиражей.
- Миграция `0040_fast_jackpot_odds` сначала фиксирует текущие правила в snapshot всех запланированных FLASH и PULSE, затем меняет только настройки будущих тиражей. Безопасный downgrade блокируется после появления тиражей нового формата.
- Bootstrap и демонстрационные данные Mini App синхронизированы с диапазонами 3/20 и 2/12 + 2/6; регрессии проверяют старые форматы, выплаты и новые вероятности 1/1 140 и 1/990.

### Восстановление настроек лотерей в панели владельца

- Production-журнал подтвердил успешное изменение текущего джекпота и отсутствие последующего запроса конфигурации. Причиной была общая строка аудита: после первой операции она очищалась, молча переводя обе кнопки в disabled.
- Для карточки лотереи задан безопасный стандартный комментарий аудита, он больше не очищается после операции. Ошибки API закрывают модальное подтверждение и показываются как доступное сообщение `alert`.
- Оба действия карточки переведены с глобального modal overlay на локальное inline-подтверждение; остальные действительно опасные операции панели сохранили прежний сценарий.
- Добавлен регрессионный сценарий последовательного изменения текущего джекпота, а затем цены билета и базового джекпота.

## [1.36.0] - 2026-09-15

### Предрассчитанные Interesting Facts

- Добавлены отдельные таблицы ежедневных пакетов и фактов. Уникальный пакет на московскую дату делает запуск идемпотентным, включая повторный старт scheduler после простоя.
- Scheduler запускает анализ в 04:10 МСК и один раз при старте для восстановления пропущенного дня. Ошибка контентной аналитики изолирована и не блокирует подготовку или расчёт тиражей.
- Снимок строится несколькими агрегирующими SQL-запросами по ограниченным временным окнам; карточки, score и структурированные числовые значения сохраняются заранее. API страницы читает только готовые записи.
- Сервис кандидатов отделён от API и интерфейса. Поле `fact_type` и JSON-значения оставляют точку расширения для последующей генерации текста поста без изменения исторических фактов.
- Для Bingo намеренно не создаётся статистика частых шаров: полный протокол содержит почти весь диапазон и не даёт содержательного факта. Добавлены регрессионные тесты типов кандидатов и идемпотентного пропуска повторного расчёта.
- Полный release-check пройден: 215 backend-тестов, 71 тест Mini App, 24 теста панели владельца и web smoke; Ruff, mypy, lint, typecheck и три production-сборки завершились успешно.

## [1.35.1] - 2026-09-15

### Физичнее выглядящий лототрон 6 из 36

- Диапазоны 1–9, 10–19, 20–29 и 30–36 получили стабильные цветовые классы, единые для барабана, выходного шара, накопительного лотка и совпадений лучшего билета.
- Механическая сцена дополнена бликом стекла, внутренней разметкой барабана, индикатором работы, затвором канала, подписью приёмника и коротким эффектом фиксации. Используются только transform, opacity и короткие локальные эффекты; тяжёлое 3D и новые изображения не добавлялись.
- Серверный timeline, результаты и длительность эфира не менялись. Проверены lint, typecheck, 10 целевых тестов и production-сборка Mini App; автоматическая визуальная проверка недоступна из-за отсутствия браузерной поверхности в среде.

## [1.35.0] - 2026-09-15

### Изолированная репетиция эфира

- В админскую сессию добавлен настроенный публичный адрес Mini App; API получает его из production-конфигурации, секреты или дополнительные полномочия клиенту не передаются.
- Админка формирует ссылку на специальный статический preview-режим для `pll`, `pss`, `khan`, `weekly`, `september`, `grob` и `bingo`. Fast-коды отвергаются на стороне Mini App.
- Preview перехватывает только запросы Mini App и отдаёт синтетический live-feed с выигрышным либо проигрышным демонстрационным билетом. База данных, ledger, scheduler, Telegram и настоящие результаты не вызываются.
- Для Bingo добавлена ускоренная тестовая последовательность, для 6 из 36 используется существующий лототрон и лучший билет. Каждый новый запуск начинает пятисекундный отсчёт заново.
- Проверены Ruff и 21 тест админского backend, typecheck и целевые тесты Mini App и панели владельца; обе затронутые frontend-сборки собраны для production.

## [1.34.0] - 2026-09-15

### Лототрон 6 из 36 и адаптивные часы

- Для `khan` добавлен отдельный серверный presentation timeline: 4 секунды перемешивания, выдача шести шаров с интервалом 3,2 секунды и завершение через 23,2 секунды. Денежная логика и неизменяемый результат тиража не затронуты.
- Во время эфира сервер выбирает лучший билет только по открытому префиксу выигрышной комбинации. Это исключает утечку будущих чисел; после эфира снова выдаются обычные три итоговых билета.
- Повторное чтение последнего завершённого тиража в одном live-feed устранено: готовая проекция переиспользуется в `latest_completed` и архиве.
- В Mini App добавлена самостоятельная сцена лототрона 6 из 36 и живая карточка текущего лучшего билета.
- Глобальный clock-render переведён на 10 секунд для спокойных экранов и на 1 секунду только для близкого тиража или активного эфира. Декоративные анимации не менялись.
- Проверены Ruff, 5 тестов timeline, 6 тестов LiveView, lint и production-сборка Mini App.

## [1.33.2] - 2026-09-15

### Компактное «Моё» и короткая покупка обычных билетов

- Убраны избыточные минимальные высоты карточек кабинета, баланс возвращён в одну строку с профилем, статистика собрана в компактный ряд, а пустой best-win hero скрывается.
- Для всех стандартных picker, кроме короткого ПЛЛ 2:22, добавлена верхняя one-tap покупка случайных пакетов с проверкой баланса и лимита игрока. Она вызывает существующую идемпотентную прямую покупку и остаётся внутри выбранной лотереи.
- Двойная визуальная индикация прямой покупки в стандартном picker убрана; корзина сохранена как отдельный осознанный сценарий.
- Проверки ограничены изменённым Mini App-сценарием, lint и production-сборкой.

## [1.33.1] - 2026-09-15

### Точечная разгрузка Mini App

- Частота общего clock-render снижена с 5 до 1 раза в секунду; dashboard, highlights и проверка версии переведены с короткого polling на часовой, а Fast SSE больше не запускает полное обновление dashboard на каждом событии.
- Главная бегущая строка выполняет один медленный проход вместо бесконечной анимации. Живые эфиры и обновление при возврате приложения на экран сохранены.
- Исправлена вложенная стилизация суммы джекпота Fast, из-за которой цифры визуально пропадали.
- Окно purchase limiter сокращено до 5 секунд, клиентская ошибка 429 локализована и автоматически скрывается через 4,5 секунды.
- Выполнены только целевые проверки изменённых backend- и Mini App-сценариев, без полного набора проекта.

## [1.33.0] - 2026-09-15

### Финальная диспетчерская владельца

- Dashboard получил московскую суточную проекцию без новой таблицы: завершённые тиражи считаются по расписанию, продажи — по времени покупки, выплаты — по времени расчёта; итог явно определён как продажи минус выплаты.
- Счётчики dashboard теперь корректно учитывают выбранную область обычных или Fast-игр. Для Fast добавлена отдельная красная control-room проекция с текущими раундами и историческими результатами.
- В ответ игрока добавлены активные билеты и время последней попытки автоучастия. Ошибки автоучастия сохраняются стабильными кодами: недостаток средств, лимит, закрытые продажи, неподходящая комбинация и техническая ошибка.
- Все изменяющие состояние действия в интерфейсе владельца получили второй шаг с точным сравнением «было → станет», причиной аудита и напоминанием о неизменяемости завершённых тиражей.
- Mini App получил CSS-знак валюты, доступную точную подпись для скринридера и единое сокращение сумм от миллиона. Схема данных и денежный ledger не менялись.
- Проверены Ruff, mypy, все 210 backend-тестов, 22 теста панели владельца и 68 тестов Mini App; обе frontend-сборки успешно собраны для production.

## [1.32.0] - 2026-09-15

### Надёжное подтверждение и продолжение покупки

- Подтверждённый сервером результат покупки отделён от последующего обновления dashboard/account: сетевой сбой синхронизации не показывает ложную ошибку и не провоцирует повторную покупку.
- Баланс, общие и пользовательские счётчики, а также число билетов текущего тиража обновляются оптимистично из авторитетного `PurchaseResult`; затем проекции сверяются с сервером в фоне.
- Закреплённая панель обычного picker получила быстрый случайный выбор. Kasper Bingo остаётся в кассе после оплаты, обновляет подборку и «Мои билеты» без смены вкладки и показывает компактный переход к купленным билетам.
- Для полностью купленной корзины добавлен отдельный итоговый экран с продолжением покупки, переходом к активным билетам или на главную. Частичная ошибка по-прежнему оставляет непроданные позиции в корзине.
- Добавлены регрессии на успешную покупку при недоступной фоновой синхронизации, быстрый случайный выбор, новый итог корзины и сохранение вкладки Bingo. Mini App: lint, typecheck и 67 тестов — успешно.

## [1.31.0] - 2026-09-15

### Непрерывная покупка и визуальная связность

- Успешная прямая покупка больше не закрывает lottery room. Купленная комбинация очищается, данные выбранной лотереи обновляются из свежего dashboard, а компактное уведомление не прерывает следующий выбор.
- Действия «В корзину» и «Купить» закреплены у нижнего края picker-экрана; контент получил безопасный нижний отступ и поддержку Telegram safe area.
- В Kasper Fast удалён предварительный объясняющий блок. Карточки игр идут сразу после заголовка, а последний джекпот и переход к билетам собраны в нижний служебный блок.
- Сетка эфира PULSE расширена с жёсткой схемы 2+1 до 2+2. Кабинет визуально переведён на отдельные зелёно-золотые редакционные карточки без изменения данных или поведения.
- Проверены typecheck, lint, все 66 тестов и production-сборка Mini App; отдельно проверена версия backend-приложения и визуально просмотрены обычный picker, PULSE, Kasper Fast и кабинет.

## [1.30.0] - 2026-09-15

### Главная как афиша

- Главная Mini App получила компактную афишу из ближайшего тиража и трёх следующих обычных событий; Kasper Fast по-прежнему не рекламируется вне своего раздела.
- Карточка «Вы в игре» собирается из уже загруженных проекций лотерей, показывает только участие в обычных играх и ведёт к отфильтрованным активным билетам.
- Dashboard дополнен двумя общими счётчиками билетов. Они вычисляются одним агрегатным запросом без новой таблицы, фоновой задачи или миграции; выплаты месяца и текущие джекпоты переиспользуют существующие данные.
- Для ленты статистики и декоративных акцентов используются только CSS; режим уменьшенного движения останавливает анимацию.

## [1.29.0] - 2026-09-15

### Kasper Fast и более редкие джекпоты

- FLASH переведён с 3/15 на 3/16, PULSE — с 2/10+1/5 на 2/10+2/5. Для PULSE сохранена прежняя лестница: одно совпадение платит 88 CAS, два или три — 888 CAS, полное 2+2 делит джекпот.
- Миграция `0038` сначала фиксирует прежние ruleset/размеры в снимках всех запланированных тиражей и только затем обновляет настройки лотерей. Покупка, dashboard и auto-play читают формат целевого тиража, поэтому 120 уже купленных производственных билетов не меняются и не возвращаются.
- Mini App использует серверные размеры обоих полей для ручной и быстрой случайной покупки, показывает четыре позиции нового PULSE и 16 позиций нового FLASH.
- `Kasper Fast` выделен красным в навигации и получил отдельный красно-чёрный фон экрана. Реклама быстрых игр с главной убрана; вход, эфир, джекпот и вся накопленная история находятся в одном разделе.
- Производственный bootstrap обновлён вместе с миграцией, чтобы при каждом старте не возвращать устаревшие форматы.
- Выполнены целевые проверки финансовой логики и перехода: Ruff, mypy, 57 backend-тестов, 32 теста Mini App и offline SQL миграции `0038`.

## [1.28.0] - 2026-09-15

### Тихие уведомления

- Settlement больше не ставит в Telegram outbox обычные результаты, включая auto-play. Новое событие `JACKPOT_WIN` создаётся только победителю джекпота и содержит его фактическую долю выигрыша.
- Миграция `0037` расширяет ограничение типа и отменяет ещё не доставленные старые покупки/результаты. История отправленных сообщений не меняется.
- Mini App не считает и не выдаёт устаревшие `DRAW_RESULT`; новые обычные Fast-результаты также не создаются. В ленте остаются важные выигрыши, джекпоты и приглашения, а все результаты доступны в билетах.
- Текст настройки Telegram обновлён под два оставшихся сценария: личный джекпот и напоминание после 24 часов без покупок.
- Проверены только затронутые зоны: Ruff, mypy трёх backend-модулей, 41 backend-тест уведомлений/settlement/read models, 26 тестов Mini App, его typecheck/lint и offline SQL миграции `0037`.

## [1.27.1] - 2026-09-15

### Исправление поиска Bingo по трём числам

- Убраны ошибочные `ge/le`-ограничения с массива повторяющихся query-параметров `number`; диапазон и уникальность по-прежнему проверяются доменным `BingoQueryService` для каждого числа.
- Поиск принимает от одного до трёх заполненных полей. Ошибка ответа остаётся внутри карточки поиска и не дублируется ложным сообщением о найденных билетах.
- Добавлены backend-регрессия на разбор повторяющихся `number` и Mini App-тесты на поиск по одному, двум и трём числам, проверку уникальности и локальное отображение ошибки.
- Полный `scripts/check.ps1` прошёл: Ruff, форматирование, mypy, 199 backend-тестов, 65 Mini App-тестов, 22 Admin-теста, Web smoke-тест, а также lint/typecheck/build всех клиентов.

## [1.27.0] - 2026-09-15

### Компактная покупка, доступный поиск Bingo и рабочая админка

- Удалены блокирующие `PurchaseConfirmation` и автоматический post-purchase запрос Telegram write access. Все успешные действия используют компактный auto-dismiss status; ошибки остаются явными и не исчезают автоматически.
- Поиск свободного Bingo-инвентаря принимает три уникальных числа. Валидация и пустой результат находятся в том же блоке, поэтому пользователю не нужно искать сообщение прокруткой; набор Каспера с четырьмя фиксированными числами сохранён.
- Admin draw detail получил сохранённый `bingo_result` каждого билета без изменения схемы данных. На его основе интерфейс показывает три категории, число победителей, ход закрытия, сумму выплат, участников и выигрышные билеты.
- 58 шаров Bingo заменены в таблицах на компактное число ходов и два не выпавших шара. Полная последовательность доступна по раскрытию. Bingo удалён только из частотной статистики, где почти каждый шар выпадает в каждом тираже и не даёт полезного сравнения.
- Управление auto-play теперь передаёт выбранное владельцем количество от одного до пяти билетов и показывает состояния «работает», «ожидает первого тиража» и «требует внимания».
- Добавлены backend и frontend регрессии для Bingo stage results, компактного подтверждения покупки, трёх любимых чисел, локальной ошибки поиска, Admin Bingo summary и настройки количества auto-play.
- Browser QA недоступен: Computer Use не обнаружил подключённых приложений или браузеров. Проверка выполнена компонентными тестами, typecheck, lint и production-сборками.
- Полный `scripts/check.ps1` прошёл: Ruff, форматирование, mypy, 198 backend-тестов, 63 Mini App-теста, 22 Admin-теста, Web smoke-тест, а также lint/typecheck/build всех клиентов.

## [1.26.0] - 2026-09-14

### Быстрые покупки Fast и исправление автоучастия

- Карточка каждой Fast-лотереи показывает актуальный jackpot без дополнительного
  API-запроса: используется уже загруженная проекция dashboard.
- Добавлены прямые покупки 1/5/10 криптографически случайных билетов. Кнопки
  учитывают остаток лимита игрока, лимит одной покупки, баланс и статус продаж;
  вся пачка проходит одной идемпотентной транзакцией и одной записью покупки.
- Клавиатура CODE переставлена в привычный телефонный порядок 1–9 и нижний 0;
  правила четырёхзначного кода, повторы и существующее оформление сохранены.
- Production-аудит до исправления подтвердил источник дефекта: включено шесть
  настроек auto-play, пять не принадлежали владельцу, а три из них ни разу не
  запускались. Планировщик передавал в сервис фильтр владельца независимо от
  выбранного в Admin Panel игрока.
- Фильтр снят только в штатном планировщике. Персональные настройки, лимит пяти
  билетов, проверки баланса, idempotency key и immutable ledger не изменены.
- Добавлены регрессии на прямую Fast-покупку, отображение jackpot, телефонный
  порядок CODE и запуск scheduler auto-play без owner-only фильтра.
- Полный `scripts/check.ps1` прошёл: Ruff, форматирование, mypy, 197 backend,
  62 Mini App, 19 Admin и 1 Web тест, а также lint/typecheck/build всех клиентов.
  Визуальный browser QA недоступен: Computer Use не обнаружил браузеров.

## [1.25.0] - 2026-09-14

### Новая механика и касса Kasper Bingo

- Относительные «первые закрывшие» туры заменены фиксированными границами
  18/34; расчёт делит целые призовые пулы между всеми подходящими проданными
  билетами, сохраняя детерминированное распределение остатка по официальному
  номеру. Джекпот по-прежнему требует полный билет к 28-му ходу.
- Позиция заготовки отделена от официального номера билета. Миграция 0036
  сохраняет историю, сбрасывает следующий Bingo-номер к следующему номеру
  после реально проданного максимума и не расходует номера на новые пулы.
- Транзакционная покупка умеет выбирать свободные билеты сервером, фильтровать
  их по обязательным числам и присваивать одной пачке непрерывные номера.
  Добавлены 1/5/10/все доступные, поиск по пяти числам и запас ограниченных
  «Наборов Каспера» с 2/9/16/28; текущий открытый пул дополняет миграция только
  за счёт непроданных заготовок.
- Live feed кэширует публичный итог категорий один раз на раскрытый ход внутри
  процесса. Клиент сам выбирает лучший из пользовательских билетов и сохраняет
  обычный двухсекундный polling без WebSocket-инфраструктуры.
- Mini App получила компактную live-компоновку и нижнюю закреплённую панель
  категорий. Игровые правила в интерфейсе сокращены до двух абзацев.
- Полный `scripts/check.ps1` прошёл: Ruff, форматирование, mypy, 196 backend-тестов,
  60 Mini App-тестов, 19 admin-тестов, web smoke-тест, lint/typecheck и production
  build всех трёх клиентов. Локальный PostgreSQL и браузерный
  контроллер были недоступны; миграция дополнительно сверена с именами
  production-ограничений перед выпуском.

## [1.24.1] - 2026-09-05

### Выбор чисел «3 СЕНТЯБРЯ»

- Числовое поле принудительно поднято над декоративными слоями, а всем 33
  кнопкам возвращены стабильные размеры и обработка касания в Telegram WebView.
- По срочному указанию владельца выполнены только production build и проверка
  доступности; резервная копия и тестовый набор пропущены.

## [1.24.0] - 2026-09-05

### Общий счётчик тиражей в обзоре

- На главный экран админ-панели выведено уже существующее серверное значение
  `completed_draws`: учитываются только завершённые тиражи всех лотерей.
- Дополнительный запрос к базе не добавлялся; счётчик загружается вместе с
  обычными данными обзора.

## [1.23.1] - 2026-09-05

### Регистрация Web-игрока

- Исправлен порядок `flush` при создании связки `User → Balance/WebAccount`.
  PostgreSQL больше не отклоняет новый баланс по внешнему ключу, а регистрация
  завершается welcome grant через ledger.
- Диагноз подтверждён на production PostgreSQL безопасной транзакцией с
  принудительным rollback; пользовательские данные при проверке не создавались.

## [1.23.0] - 2026-09-05

### Desktop Web и поле «3 СЕНТЯБРЯ»

- Возвращён отдельный desktop-only React/Vite-клиент на `/web/`. Он использует
  существующие application services и production-базу: отдельной копии игровой
  логики, балансов или тиражей нет.
- Реализованы самостоятельная регистрация, Argon2-пароли, подписанная
  Secure/HttpOnly cookie, CSRF-защита мутаций и welcome grant через immutable
  ledger. Существующая таблица `web_accounts` позволила обойтись без миграции.
- Web API покрывает dashboard, account, пагинированные tickets, live feed,
  универсальную покупку стратегий и пул Kasper Bingo. Fast-эфир следует
  серверным `live_starts_at`, `reveal_at` и `live_ends_at`.
- Gateway и единый release-скрипт теперь собирают и публикуют третий frontend;
  Mini App остаётся корневым Telegram-интерфейсом, Web изолирован в `/web/`.
- В CSS «3 СЕНТЯБРЯ» устранён конфликт старых theme-правил: board, groups и
  buttons имеют явные display/visibility/min-size, поэтому поле не схлопывается.
- Проверки релиза: Ruff/format и mypy — чисто; backend — 195 passed; Mini App —
  57 passed; Admin — 19 passed; Web — lint/typecheck/build и 1 passed.

## [1.22.1] - 2026-09-05

### Auto-play после смены формата

- Production smoke v1.22.0 обнаружил переходный случай: возвращённые
  `AUTO_PLAY`-билеты продолжали блокировать повторную покупку в том же draw.
- Выбор кандидатов теперь учитывает только действующие билеты `PURCHASED`, а
  idempotency key включает `ruleset_code`. Поэтому новый формат может безопасно
  получить новый автобилет, не дублируя действующие билеты других лотерей.
- Добавлена регрессия CODE auto-play с повторяющимися цифрами и отдельным ключом
  стратегии. Проверки: Ruff/format/mypy — чисто; backend — 191 passed; secret
  scan — чисто.
- Исправление: commit `1cf9ec9`.

## [1.22.0] - 2026-09-05

### CODE вместо SHADOW без сброса истории

- Стабильный технический код `shadow` намеренно сохранён: sequence тиражей и
  билетов продолжаются без создания второй lottery entity. Новые будущие
  тиражи используют стратегию `code_4_digits`.
- Универсальная стратегия расширена ordered-комбинациями, нижней границей 0 и
  повторами. CSPRNG независимо генерирует четыре позиции; match считается по
  позиции. Категория одна: 4/4 делит весь jackpot, остальные результаты равны 0.
- Миграция `0035_shadow_to_code` сохраняет фактические ticket price, base и
  текущий jackpot. Несовместимые будущие билеты переводятся в `REFUNDED` с
  парными `TICKET_REFUND`-проводками пользователя и jackpot; завершённые
  тиражи не меняются. Операция фиксируется в owner audit.
- Mini App получает `ruleset_code` и показывает CODE как отдельный продукт:
  цифровая сцена без тяжёлого ассета, keypad 0–9, повторы, удаление последней
  цифры, криптографический случайный код, четыре позиции эфира и позиционная
  подсветка бумажного билета. Анимации используют только transform/opacity и
  отключаются при `prefers-reduced-motion`.
- Документация расписания, архитектуры и решений обновлена; исторический аудит
  SHADOW оставлен неизменным.
- Проверки: Ruff и format — чисто; mypy — чисто; backend — 190 passed;
  Mini App — lint/typecheck/build и 57 passed; Admin — lint/typecheck/build и
  19 passed; Alembic head — `0035_shadow_to_code`; secret scan — чисто.
- Реализация: commit `b2233a7`.

## [1.21.2] - 2026-09-05

### Немедленный второй слот «2:22» и проверка выбора чисел

- Будущие тиражи «2:22» №52 и №53 выстроены по уже утверждённому расписанию:
  5 сентября 13:45 и 6 сентября 02:22 МСК. После проведения планировщик
  продолжит общую последовательную нумерацию и подготовит следующий слот.
- 124 билета из двух ещё не проведённых тиражей переводятся в `REFUNDED`.
  2 976 000 CAS возвращаются пользователям через `TICKET_REFUND` в immutable
  ledger; та же сумма компенсирующе списывается с jackpot account. Тиражи и
  номера билетов не удаляются, завершённая история не меняется.
- Добавлена необратимая data migration `0034_pll_second_slot`. Операция
  записывает owner audit и требует точного ожидаемого состояния production,
  чтобы не перенести посторонние тиражи.
- Для обычных лотерей добавлена регрессия выбора чисел в «2:22», ПСС-Лото и
  «3 сентября»; существующие проверки покрывают ГРОБ, «6 из 36» и два поля
  Kasper Grand. Fast-код и Fast-интерфейс не менялись.
- Выпуск затрагивает API/планировщик и данные. Опубликованная сборка Mini App
  остаётся 1.21.1: проверка интерфейса не потребовала изменения его кода.
- Проверки: Ruff и mypy прошли; backend — 187 passed; адресная проверка Mini App
  — 26 passed, затем typecheck и lint прошли. Alembic head:
  `0034_pll_second_slot`; secret scan staged diff — чисто.
- Production: commit `6427766`, обновлён только API. Миграция применена,
  health приложения и PostgreSQL — `ok`. В production подтверждены нулевые
  продажи у перенесённых тиражей №52/53, 117+7 билетов в `REFUNDED` и
  сбалансированные проводки возврата на 2 976 000 CAS.
- Контроль в реальном времени: тираж «2:22» №52 проведён 5 сентября в 13:45
  МСК как пустой и получил результат `4, 5, 11, 12`; №53 оставлен на 02:22,
  №54 автоматически создан планировщиком на 13:45 следующего дня.

## [1.21.1] - 2026-09-05

### Визуальные темы лотерей

- Gateway-only косметический выпуск; backend остаётся 1.21.0. Имя «2:22» — отображаемый бренд в Mini App/Admin; code pll и база, старые записи, финансы и расписания не меняются.
- Новый отдельный lottery-themes.css загружается после legacy styles; старый конфликтующий picker-heading заменён чистой selection-heading. Разные палитры ordinary игр вместо общей зелёной.
- Две иллюстрации созданы встроенным imagegen и сохранены в assets; сжатие JPEG без изменения композиции. Для этих сцен отключён дублирующий foreground, а невидимые сцены приостанавливают CSS-анимации.
- Ассеты и промпты: docs/DESIGN_1211.md.
- По прямому указанию владельца новые тесты и полный прогон не выполняются. Проверяются frontend lint и сборки; финансовая резервная копия для gateway-only косметики пропускается. Миграций и перезапуска API/бота нет.
- Браузерный визуальный smoke остаётся недоступен из-за ранее полученной блокировки запуска браузера автоматической проверкой разрешений.
- Публикация 68d56fb выполнена через gateway-only release с пропуском backup по прямому указанию владельца. Обе frontend-сборки и Mini App lint прошли; тесты не запускались. API/бот/DB не пересоздавались.
- Production: страницы и health 200, JS/CSS и две JPEG-иллюстрации совпадают со сборкой, manifest 1.21.1; админка без авторизации 401. После одного внешнего TLS reset повторная проверка Admin успешна.


## [1.21.0] - 2026-09-05

### Навигация, каталог и разделение Fast

- Добавлены Discovery/Today/Catalog/LotteryRoom; удалён прежний перегруженный storefront и постоянная нижняя кнопка эфира.
- Общий SQL scope standard/fast/all применяется до LIMIT/OFFSET к билетам, их количеству, тиражам, расписанию, jackpot history/агрегатам и аналитике. Старые API-вызовы без scope совместимы.
- Highlights возвращает только ближайшее событие и последний джекпот выбранного типа игр. Эфир обычной комнаты запрашивает конкретный lottery_code.
- Админка больше не скачивает всю историю Fast циклом; страницы по 100, фильтры периода и типа игры на сервере. Общий фонд и пользователи явно обозначены общими.
- Изменения только в чтении и интерфейсах: схема, бизнес-правила, расчёты и ledger не менялись.
- Регрессии покрывают выбор/просмотр Bingo, четыре пункта меню, каталог, фильтрацию Fast до пагинации и эфир выбранной игры.
- Браузерный визуальный smoke недоступен: CUA не предоставил браузеров, предыдущую попытку запуска Chrome отклонила автоматическая проверка разрешений (blocked by policy). Обход блокировки не выполняется.
- Backend, Mini App и Admin: 1.21.0.
- READ ONLY / REPEATABLE READ smoke кандидата на production прошёл: ordinary/Fast/all = 3040/4213/7253 билета; 0/13/13 джекпотов; 0/43201070/43201070 CAS. Проверены страницы, расписание, activity, operational status, highlights и эфир конкретной лотереи. Данные не изменялись.
- Итоговый backend-прогон: 186 тестов прошли сразу; единственное устаревшее ожидание версии исправлено на 1.21.0 и test_app перепроверен (4/4). Итого 187 backend-тестов. Ruff/format/mypy прошли. Mini App: typecheck/lint/build и 53 теста прошли. Admin: typecheck/lint/build, 18 прежних тестов и новая проверка scope прошли; исправлены ожидание доступного имени кнопки и ожидание закрытия диалога в тестах. Всего проверено 259 тестов. Публикация: commit ad2b692, api + gateway, бот без пересоздания.
- Backup создан до публикации, проверка восстановления и Alembic check прошли, новых операций миграции нет. API/DB healthy; scheduler без ошибок.
- После публикации повторный read-only smoke на коде 1.21.0 подтвердил разделение и равенство итогов. Обе HTTPS-страницы и health отвечают 200, JS/CSS совпадают с локальной сборкой; manifest 1.21.0, анонимный Admin dashboard возвращает 401. Один внешний TLS-запрос получил reset; повторная проверка полностью прошла.


## [1.19.0] - 2026-09-05

### Понятная админка и проверка Fast

- Read-only аудит production: по 328 завершённых тиражей FLASH/SHADOW,
  1 627/1 626 рассчитанных билетов, 1/10 джекпотных тиражей. Совпадения, сроки
  покупки, итоговые выплаты и jackpot ledger сверены без расхождений.
- Production использует random.SystemRandom; SHA-256 модуля lottery_rules
  совпал с проверенным локальным кодом. RNG и бизнес-правила не менялись.
  Подробности и ограничения статистической оценки — в docs/FAST_RANDOM_AUDIT_2026-09-05.md.
- Jackpot read model: суммы/максимумы по всей истории, inactive лотереи,
  per-lottery latest через row_number, явное событие джекпота в draw detail.
  Дополнительных таблиц и миграций нет. API расширен совместимо.
- Реальные новые SQL-запросы выполнены внутри READ ONLY / REPEATABLE READ
  транзакции без замены production-кода. 13 джекпотных тиражей, 43 201 070 CAS,
  10 строк лотерей; суммы и счётчики сошлись с прежним общим отчётом.
- Админка: сводка владельца, точные CAS, последние выплаты с переходом в тираж,
  адаптивная вёрстка, отдельный System, обновление и обработка ошибок.
- Backend/Admin 1.19.0, Mini App остаётся 1.18.1; релиз затронет api и gateway.

Проверки перед выпуском: scripts/check.ps1 прошёл целиком — Ruff/format/mypy,
173 backend-теста, 48 Mini App-тестов, 18 Admin-тестов, typecheck/lint/build
обоих интерфейсов. Read-only smoke новых SQL на production также прошёл.
Визуальный браузерный smoke недоступен:
CUA вернул пустой список браузеров. React-проверки не заменяют осмотр реальной
вёрстки в браузере владельца; это ограничение проверки сохраняется явно.

Публикация: commit `f15d13d`, `release_vps.py --services api gateway` выполнен.
Backup создан до загрузки, pg_restore --list и Alembic check прошли без новых
операций миграции. API/DB healthy, бот продолжает работу. Production API 1.19.0;
13 джекпотных тиражей и 43 201 070 CAS сверены повторно, разбивка по 10 лотереям
сходится с общим итогом, последние выплаты открывают правильные тиражи.
Оба HTTPS-сайта и /health — 200, опубликованные CSS/JS совпали с локальной
сборкой по SHA-256. Анонимный /api/v1/admin/dashboard возвращает 401.
Mini App по-прежнему публикует manifest 1.18.1; модуль RNG остался прежним.

## [1.18.1] - 2026-09-05

### Fast и личный кабинет — исправления Mini App

- Часы один раз привязываются к серверу с поправкой на половину HTTP RTT,
  затем идут по performance.now(). SSE и последующие dashboard не меняют отсчёт;
  после возвращения из фона выполняется новая привязка к серверу.
- Закрыт промежуток scheduled_at → live_starts_at: завершённый тираж показан
  в starting без преждевременного раскрытия чисел. Устаревшие снимки отсеиваются.
- Убрана оценочная высота content-visibility у Fast; фазы эфира получили
  стабильные строки, текст toast — отдельную сжимаемую колонку.
- Vite выпускает version.json; Mini App проверяет именно gateway, независимо
  от версии backend. HTML и manifest перевалидируются через Cache-Control.
- Обзор «Моё»: крупный баланс, навигация с иконками, активные билеты и история,
  понятная подпись разницы выигрышей и расходов. Защищены ответы сменённых фильтров.
- Релиз только gateway: backend/admin остаются версии 1.18.0, Mini App — 1.18.1.
  Бизнес-правила и схема БД не менялись.

Проверки: Ruff, format, mypy; backend 171 passed; Mini App 48 passed; Admin
12 passed; typecheck/lint/build обоих интерфейсов. HTTP smoke локального Mini App
вернул 200, production-сборка содержит version.json с 1.18.1.
Первый полный прогон остановился на неверном ожидаемом времени в новом тесте
(SHADOW в fixture стартует через 10 минут, не 6); ожидание исправлено,
frontend-проверки продолжены и прошли. Backend повторно не запускался.
Визуальный smoke в браузере недоступен: CUA вернул пустой список браузеров.
Проверку Telegram WebView на устройстве владельца не подменяем тестами jsdom.

Публикация: commit `5ed4405`, `release_vps.py --services gateway` выполнен;
PostgreSQL backup создан до загрузки релиза. API и PostgreSQL healthy,
бот продолжает работу, пересоздан только gateway. Оба HTTPS-сайта и /health
вернули 200; JavaScript на обоих сайтах побайтово совпал с локальной сборкой
(SHA-256). Mini App отдаёт version.json = 1.18.1 и Cache-Control no-cache;
HTML обоих сайтов также требует перевалидации. Последняя правка анимации
Fast дополнительно прошла typecheck/lint, 3 FastView-теста и релизную сборку.

## [1.18.0] - 2026-09-04

### Призовая лестница «6 из 36»

Сделано:

- стратегия `classic_6_36` получила отдельные коэффициенты для всех согласованных
  выигрышных категорий 2/6–5/6;
- цена новых билетов увеличена с 24 000 до 48 000 CAS;
- базовый джекпот увеличен с 24 000 000 до 30 000 000 CAS, текущий накопленный
  джекпот при этом не изменяется;
- конфигурация подготовленных тиражей обновляется миграцией, а уже купленные
  билеты сохраняют собственную неизменяемую цену покупки;
- изменение цены и базы записывается в аудит администратора.

Теперь система работает так:

- 2 совпадения выплачивают 12 000 CAS, 3 — 48 000 CAS, 4 — 480 000 CAS,
  5 — 4 800 000 CAS, а 6 совпадений делят весь текущий джекпот;
- обычные призы оплачивает Фонд Каспера, джекпот расходуется только при полном
  совпадении;
- после выигрыша джекпот восстанавливается до новой базы 30 000 000 CAS.

Технически:

- migration: `0032_classic_prizes`;
- tests: 171 backend + 40 Mini App + 12 Admin Panel passed; Ruff, mypy, lint,
  typecheck и production builds passed;
- Alembic: единственная head `0032_classic_prizes`;
- commit: `33ee3be`.

## [1.17.0] - 2026-09-04

### Классическая лотерея «6 из 36»

Сделано:

- для сущности `khan` добавлена универсальная стратегия `classic_6_36` с выбором
  6 чисел из 36;
- сохранена действующая схема выплат: 2 совпадения — 50% цены билета,
  3 совпадения — 300%, полное совпадение делит джекпот; 4 и 5 совпадений
  не образуют отдельной призовой категории;
- будущие билеты старого формата переводятся в `REFUNDED` с полным возвратом
  пользователям и парной записью по джекпоту в immutable ledger;
- миграция сохраняет идентификаторы и последовательности тиражей и билетов,
  обновляет только конфигурацию ещё не проведённых тиражей и записывает действие
  в аудит администратора;
- для Mini App создана отдельная классическая сцена с лототроном, шарами,
  сине-золотой палитрой, круглым полем 1–36 и пометкой «Классика»;
- старые локальные записи корзины с четырьмя числами автоматически отбрасываются
  после получения новой серверной конфигурации;
- проверены будущие конфигурации остальных ранее изменённых лотерей: дополнительный
  переход им не требуется.

Теперь система работает так:

- тиражи «6 из 36» проходят ежедневно в 09:00 и 18:00 МСК;
- билет содержит ровно шесть уникальных чисел от 1 до 36 и стоит 24 000 CAS;
- текущий джекпот после перехода равен 33 456 000 CAS, базовый — 24 000 000 CAS;
- завершённая история не меняется, а следующие номера продолжают прежние счётчики.

Технически:

- migration: `0031_khan_classic`;
- tests: 171 backend + 40 Mini App + 12 Admin Panel passed; Ruff, mypy, lint,
  typecheck и production builds passed;
- Alembic: единственная head `0031_khan_classic`; локальный `alembic check`
  недоступен без локального `DATABASE_URL`, миграция будет проверена при релизе;
- commit: `dba77d3`.

## [1.16.3] - 2026-09-04

### Стабильный переход Fast-карточки в эфир

Сделано:

- найдено расхождение между миграцией Fast и повторной production-инициализацией:
  bootstrap удалял `sales_cutoff_seconds` и возвращал минутный cutoff;
- Fast-расписание вынесено в единый bootstrap-конструктор с обязательным cutoff 8 секунд;
- добавлена корректирующая миграция для конфигурации и будущих подготовленных тиражей;
- добавлен регрессионный тест, запрещающий повторную потерю секундного cutoff.

Теперь система работает так:

- карточка ближайшей Fast-лотереи остаётся актуальной до восьмисекундного перехода в эфир;
- следующий тираж этой лотереи не подменяет текущий за минуту до розыгрыша;
- повторный релиз сохраняет ту же настройку.

Технически:

- migration: `0030_fast_cutoff_fix`;
- tests: 170 backend + 39 Mini App + 12 Admin Panel passed; Ruff, mypy, lint,
  typecheck и production builds passed;
- commit: `49ca81f`.

## [1.16.2] - 2026-09-04

### Новый фирменный знак Kasper Loto

Сделано:

- по утверждённому брендборду подготовлены два самостоятельных прозрачных SVG-ресурса:
  горизонтальный логотип и круглый символ;
- логотип встроен в существующую шапку без изменения расположения баланса, корзины и
  остальных элементов интерфейса;
- для экранов уже 360 пикселей предусмотрено автоматическое переключение на компактный
  символ без текста;
- круглый символ подключён как favicon и используется на экране безопасного входа;
- растровый фон брендборда в приложение не переносился.

Теперь система работает так:

- на обычном мобильном экране пользователь видит знак и надпись `Kasper Loto`;
- на очень узком экране остаётся только узнаваемый круглый знак;
- графика остаётся чёткой на Retina-экранах и не создаёт дополнительной анимационной
  нагрузки на телефон.

Технически:

- migration: не требуется, схема базы данных не менялась;
- tests: 39 Mini App + 4 точечных backend passed; Mini App lint, typecheck и build passed;
- commit: `e3a1f3c`.

## [1.16.1] - 2026-09-04

### Производительность Mini App и облегчённый выпуск

Сделано:

- добавлен клиентский бюджет фонового движения: `IntersectionObserver`
  останавливает CSS/Web Animations у сцен, ушедших за границы экрана;
- бесконечное движение слоёв иллюстраций включается только пока конкретная сцена
  видима, а при сворачивании Telegram WebView секундные часы и фоновые запросы
  приостанавливаются;
- на мобильных устройствах сохранён тот же рисунок зерна и частиц, но снижена
  частота их незаметных служебных перерисовок;
- web-сборка перенесена с VPS на локальный компьютер; на сервер отправляются
  готовые `dist`, из которых собирается лёгкий Caddy-образ;
- release-сценарий разделён на понятные этапы, одновременно читает stdout/stderr,
  имеет таймауты и больше не зависает из-за заполненного SSH-буфера;
- при обычном web-релизе исключены ненужные миграции и полное тестовое
  восстановление базы; резервная копия создаётся по-прежнему;
- с VPS удалены Navidrome, старый `k-loto-next`, rollback-каталоги, устаревшие
  образы и build-cache; сохранены только K-Loto, его данные и AmneziaVPN;
- свежая production-база сохранена и проверена вне VPS, серверу добавлен swap
  2 ГБ для защиты от редкого пика памяти.

Теперь система работает так:

- пользователь видит прежние анимации, но невидимые карточки больше не греют
  телефон в фоне;
- визуальный релиз собирается на мощностях рабочего компьютера, а VPS выполняет
  только быструю упаковку готовых файлов и перезапуск gateway;
- релиз показывает текущий этап и немедленно сообщает точное место ошибки.

Технически:

- migration: не требуется, схема базы данных не менялась;
- tests: 169 backend + 39 Mini App + 12 Admin Panel passed;
- commit: `c38d42a`.

## [1.16.0] - 2026-09-04

### Оперативная админ-панель и точный контекст джекпотов

Сделано:

- структура админ-панели собрана в восемь разделов по задачам владельца;
- журналы CAS, уведомлений и действий администратора перенесены во вкладки раздела «Система»;
- статистика билетов, чисел, финансов и сравнение игр объединены в «Аналитику»;
- добавлено лёгкое серверное агрегирование продаж и выплат по часам или дням, которое выполняется только при открытии обзора;
- расписание получило фильтры по типам лотерей, цветовые идентификаторы и автоматический фокус на ближайшем тираже;
- экран тиражей получил фильтры, а его подробности теперь раздельно объясняют сорванный джекпот и общую выплату;
- production ledger и проекция джекпотов проверены на SHADOW №0226 в 19:15 МСК.

Теперь система работает так:

- `34 млн CAS` у SHADOW читаются как совокупные выплаты джекпотами за всё время;
- для тиража №0226 отдельно виден фактический джекпот `1 019 980 CAS`, один выигрышный билет и общий итог выплат `1 020 156 CAS`;
- тяжёлые журналы не занимают главное меню, а аналитика загружается только при входе в соответствующий раздел;
- анимации Mini App не удалялись и не ослаблялись.

Технически:

- migration: не требуется, схема базы данных не менялась;
- tests: 169 backend + 38 Mini App + 12 Admin Panel passed;
- commit: 921d70e.

## [1.15.1] - 2026-09-04

### Завершение Fast-интерфейса

Сделано:

- добавлен серверный cutoff Fast длительностью 8 секунд через конфигурацию расписания;
- подготовленные будущие тиражи переводятся на новое время миграцией `0029_fast_cutoff`;
- серверная шкала раскрывает три числа за 3,5 секунды, результат показывается ещё 6 секунд;
- карточка текущего эфира закрепляется сверху до завершения результата, затем список плавно перестраивается по времени ближайших тиражей;
- декоративная пульсация PULSE заменена на единую SVG-линию ЭКГ с лёгкой анимацией прохождения импульса.

Теперь система работает так:

- продажа закрывается ровно в момент перехода карточки в восьмисекундное ожидание эфира;
- карточка не исчезает между закрытием продаж и розыгрышем;
- после короткого результата наверх плавно поднимается следующая ближайшая Fast-лотерея.

Технически:

- migration: `0029_fast_cutoff`;
- tests: 168 backend + 38 Mini App + 11 Admin Panel passed;
- commit: 0baacd2.

## [1.15.0] - 2026-09-04

### Профиль и архив билетов

Сделано:

- серверная выдача активных билетов переведена на сортировку по возрастанию времени тиража; история сохраняет обратную хронологию;
- API билетов получил пагинацию, общее количество результатов и точное количество билетов пользователя внутри каждого тиража;
- полная визуализация билета строится только по запросу пользователя и не утяжеляет длинный список;
- в read model профиля добавлены любимая лотерея и наиболее часто выбранные числа без фоновых задач и новых таблиц;
- обновлены профиль, компактные карточки, заголовки групп и состояния выбора двух полей Kasper Grand.

Теперь система работает так:

- в «Моих билетах» первым всегда расположен ближайший активный тираж, а следующая сотня загружается отдельной кнопкой;
- по тапу видны все поля билета, выбранные, выпавшие и совпавшие числа, результат и стоимость;
- профиль показывает восемь основных показателей игрока, любимую лотерею и характерные числа.

Технически:

- migration: не требуется, схема базы данных не менялась;
- tests: 166 backend + 38 Mini App + 11 Admin Panel passed;
- commit: 779b91f.

## [1.14.0] - 2026-09-04

### PULSE и трёхминутный цикл Fast

Сделано:

- добавлена стратегия `pulse_2_10_1_5` с независимой генерацией двух основных
  чисел 1–10 и одного специального Pulse-числа 1–5;
- специальное число хранится в универсальном формате как значение 11–15,
  поэтому существующие таблицы билетов, тиражей и ledger не усложнялись;
- выплаты соответствуют остальным Fast: одно общее совпадение — 88 CAS, два —
  888 CAS, полное 2+1 — собственный джекпот; 100% покупки попадает в джекпот;
- миграция создаёт PULSE с ценой 1 234 CAS и базовым джекпотом 1 234 567 CAS,
  а FLASH/SHADOW переводит на новые интервальные якоря;
- три расписания закреплены на шагах 00:00, 00:03 и 00:06 с повтором каждые
  9 минут, поэтому Fast запускается каждые 3 минуты без совпадений;
- Mini App получил отдельные красные карточку, выбор чисел и эфир PULSE,
  анимацию ЭКГ и правильное отображение комбинации 2+1 в истории;
- Admin Panel автоматически получает PULSE в расписании, настройках джекпота,
  архиве, аналитике и статистике через существующие универсальные сервисы.

Теперь система работает так:

- Fast круглосуточно повторяет цикл FLASH → SHADOW → PULSE;
- продажи закрываются за минуту, за 20 секунд карточка становится эфиром,
  числа появляются по серверной шкале, результат виден 12 секунд;
- уже созданные тиражи и купленные билеты не переписываются: планировщик
  завершает их по старому времени и затем продолжает новый точный цикл.

Технически:

- migration: `0028_pulse_fast`;
- backend tests: 166 passed;
- Mini App tests: 38 passed;
- Admin Panel tests: 11 passed;
- Ruff, mypy, frontend lint/typecheck/build: passed;
- feature commit: `50480d8`.

## [1.13.0] - 2026-09-04

### Kasper Grand 5/35 + 2/5

Сделано:

- добавлена стратегия `weekly_grand_5_35_2_5`, которая независимо валидирует и
  генерирует пять основных и два специальных числа;
- код совпадения хранит оба результата (`52` = 5+2), не меняя универсальные
  таблицы билетов, тиражей и ledger;
- категории 5+1, 5+0, 4+2, 4+1 и 3+2 получают соответственно 20%, 10%, 8%,
  4% и 2% накопительной части джекпота; пул каждой категории делится между её
  победителями;
- 5+2 делит весь джекпот, после чего базовый джекпот восстанавливается из Фонда
  Каспера;
- миграция возвращает полную стоимость старых активных билетов через две стороны
  immutable ledger, помечает их как возвращённые и переводит следующий тираж на
  новый snapshot правил;
- Mini App получила отдельные поля 1–35 и 1–5, специальное отображение билетов,
  результатов и эфира, а также компактную премиальную сцену Kasper Grand;
- Admin Panel различает основные и специальные числа и исключает старый формат
  5/20 из статистики новой стратегии.

Теперь система работает так:

- старые завершённые тиражи остаются неизменной историей;
- номер следующего тиража и глобальный номер следующего билета сохраняются;
- новые покупки, избранное, массовая корзина и владелец с автопокупкой создают
  только корректные комбинации 5+2;
- случайный результат использует два независимых вызова криптографически стойкого
  генератора; вероятность джекпота — 1 к 3 246 320.

Технически:

- migration: `0027_kasper_grand`;
- backend tests: 165 passed;
- Mini App tests: 37 passed;
- Admin Panel tests: 11 passed;
- Ruff, mypy, frontend lint/typecheck/build: passed;
- commits: `06ed284`, migration fix `5c450a1`.

## [1.12.2] - 2026-09-04

### Компактный экран выбора чисел

Сделано:

- высота декоративной сцены и заголовка покупки уменьшена для всех обычных
  лотерей;
- название лотереи и кнопка возврата сохранены, а поле чисел теперь начинается
  заметно выше;
- Fast Picker не изменялся, поскольку использует отдельную компактную композицию.

Технически:

- изменение только CSS, API и игровая логика не затронуты;
- migration: не требуется;
- commit: `d94a0fa`.

## [1.12.1] - 2026-09-04

### Стабилизация Fast-эфира

Сделано:

- проверен production-тираж SHADOW №184 за 11:30 МСК: settlement завершился в
  11:30:05, выигрышные числа и все шесть билетов сохранены корректно;
- обнаружена визуальная гонка между обновлением dashboard и SSE-эфиром: после
  settlement обычная сортировка поднимала наверх следующий FLASH, а активный
  SHADOW перемещался второй карточкой;
- активная карточка Fast теперь закрепляется первой на всё время подготовки,
  последовательного появления чисел и финального результата;
- добавлен регрессионный компонентный тест сценария, когда dashboard уже перешёл
  к следующим тиражам, а эфир завершённого SHADOW ещё продолжается.

Теперь система работает так:

- за 20 секунд до старта нужная Fast-лотерея остаётся сверху и превращается в эфир;
- после серверного settlement числа появляются в ней последовательно;
- только после короткого показа результата карточки возвращаются к сортировке по
  времени следующих тиражей.

Технически:

- migration: не требуется;
- затронут только Mini App, игровая математика и данные тиражей не менялись;
- commit: `6b7d5d6`.

## [1.12.0] - 2026-09-04

### Хронологическая витрина лотерей

Сделано:

- прежний горизонтальный переключатель заменён вертикальной витриной;
- ближайший тираж остаётся главным экраном, а остальные сущности сортируются по
  актуальному `scheduled_at` из серверного dashboard;
- Weekly исключена из обычной сортировки и закреплена финальным премиальным
  блоком недели, если она не является ближайшим тиражом;
- каждая позиция витрины использует существующую фирменную сцену лотереи,
  собственные цвета, джекпот, обратный отсчёт и безопасный переход к покупке;
- анимации реализованы средствами CSS с поддержкой `prefers-reduced-motion` и
  без дополнительных API-запросов или постоянных JavaScript-наблюдателей;
- цифровые бейджи непрочитанных уведомлений заменены нейтральной красной точкой;
- с главной удалены общий показатель выплат и случайная комбинация.

Теперь система работает так:

- после завершения тиража очередное обновление dashboard автоматически меняет
  ближайшую лотерею и порядок всей витрины;
- пользователь видит начало следующей сцены сразу под главным тиражом и может
  последовательно просматривать остальные предложения вниз по странице;
- игровая математика, покупка, расписание и settlement не изменены.

Технически:

- migration: не требуется;
- Mini App: typecheck/lint, `35 passed`, production build — успешно;
- backend metadata tests: `4 passed`;
- commit: `c120ca1`.

## [1.11.1] - 2026-09-04

### Навигация корзины и подтверждение покупки

Сделано:

- горизонтальному переключателю лотерей заданы фиксированная высота,
  горизонтальный touch-жест и устойчивый индикатор без перелетающей анимации;
- действие добавления следующего билета возвращает на главную и не очищает
  локальную корзину;
- в шапку добавлен компактный вход в непустую корзину со счётчиком комбинаций;
- окно успешной покупки закрывается крестиком или касанием фона, а кнопка
  «На главную» имеет однозначное действие;
- подпись общей выплаты за месяц приведена к понятному русскому тексту.

Теперь система работает так:

- пользователь может собирать в одной корзине несколько комбинаций и лотерей,
  свободно возвращаясь между корзиной и главной;
- после успешной покупки интерфейс не отправляет пользователя обратно к выбору
  чисел без его решения;
- `monthly_total_payout` явно обозначен как общая сумма CAS, выплаченная всем
  игрокам за текущий месяц.

Технически:

- migration: не требуется;
- Mini App: typecheck/lint, `33 passed`, production build — успешно;
- backend metadata tests: `4 passed`;
- commit: `1a8fad2`.

## [1.11.0] - 2026-09-04

### Короткий Fast-эфир и контроль джекпотов

Сделано:

- добавлен отдельный режим SSE для FLASH и SHADOW, активный только при открытой
  вкладке Fast;
- соответствующая карточка за 20 секунд до старта превращается в экран тиража:
  три пустые позиции заполняются строго сохранёнными серверными числами;
- готовый результат показывается 12 секунд, после чего интерфейс автоматически
  возвращается к покупке следующего билета;
- базовый и текущий джекпоты в Admin Panel разделены на понятные операции;
- изменение текущего джекпота защищено блокировкой строки, idempotency key,
  неизменяемой записью ledger и записью администраторского аудита;
- создание `JackpotWinEvent` распространено на Fast, при этом массовые новости о
  Fast-джекпотах по-прежнему не отправляются игрокам;
- миграция восстанавливает пропущенную статистику прежних Fast-джекпотов из
  завершённых тиражей и выигрышных билетов.

Теперь система работает так:

- короткий Fast-эфир синхронизирован с сервером и корректно восстанавливает этап
  после сворачивания или повторного открытия Mini App;
- визуальный эфир ничего не разыгрывает повторно и не влияет на RNG, settlement
  или начисление CAS;
- на дашборде владельца общая и отдельная статистика FLASH/SHADOW строится по
  полной неизменяемой истории jackpot-событий.

Технически:

- migration: `0026_fast_live`;
- Ruff, форматирование и mypy: успешно;
- backend tests: `158 passed`;
- Mini App: typecheck/lint, `33 passed`, production build — успешно;
- Admin Panel: typecheck/lint, `11 passed`, production build — успешно;
- feature commit: `5a10715`.

## [1.10.0] - 2026-09-02

### Суточное табло расписания владельца

Сделано:

- в Admin Panel добавлен раздел «Расписание» в минималистичной стилистике
  оперативного табло агента 007;
- на экран выводятся только номер тиража, название лотереи и время проведения;
- добавлены фильтр по лотерее, автоматическая подсветка и прокрутка к текущему
  или ближайшему тиражу;
- для FLASH и SHADOW оставшаяся часть текущих суток рассчитывается только для
  отображения: новые тиражи и билеты в базе не создаются.

Теперь система работает так:

- при каждом открытии вкладки сервер формирует актуальный план текущих суток по
  Москве;
- после открытия данные не опрашиваются в фоне и не создают постоянную нагрузку;
- переход на вкладку в новые сутки автоматически показывает уже новый день.

Технически:

- migration: не требуется;
- Ruff, форматирование и mypy: успешно;
- focused backend tests: `20 passed`;
- Admin Panel: typecheck/lint, `10 passed`, production build — успешно;
- feature commit: `fbb426f`.

## [1.9.1] - 2026-09-02

### Синхронизация production bootstrap

Сделано:

- production bootstrap переведён на те же пары слотов, что миграция, документация
  и локальная среда;
- предотвращён возврат расписаний к единственному старому времени при рестарте API.

Технически:

- migration: используется `0025_add_daily_slots`, новая не требуется;
- Ruff, форматирование и mypy: успешно;
- focused backend tests: `23 passed`;
- полный набор перед исправлением: backend `155 passed`, Mini App `31 passed`,
  Admin Panel `9 passed`, production-сборки успешны;
- fix commit: `9dff231`.

## [1.9.0] - 2026-09-02

### Дополнительные слоты существующих Daily-лотерей

Сделано:

- расписание ХАН расширено до `09:00/18:00`, ПЛЛ — до `02:22/13:45`,
  ПСС — до `12:00/20:30` по Москве;
- изменение выполнено на существующих lottery entities без новых счетов,
  правил или отдельных счётчиков;
- локальный development bootstrap и единый файл расписания приведены к тем же слотам;
- добавлена миграция `0025_add_daily_slots` и регрессионные тесты новых времён.

Теперь система работает так:

- планировщик поддерживает по два будущих слота каждой из трёх лотерей;
- номера тиражей и билетов продолжаются в одной последовательности внутри ПЛЛ,
  ПСС и ХАН независимо от времени проведения;
- уже созданные тиражи, купленные билеты и завершённая история не изменяются;
- существующая автопокупка владельца подхватывает новые тиражи автоматически.

Технически:

- migration: `0025_add_daily_slots`;
- Ruff, форматирование и mypy: успешно;
- backend tests: `155 passed`;
- Mini App: typecheck/lint, `31 passed`, production build — успешно;
- Admin Panel: typecheck/lint, `9 passed`, production build — успешно;
- feature commit: `af276a2`.

## [1.8.2] - 2026-09-02

### Исправление универсальной автопокупки

Сделано:

- устранена причина `ConfigurationError`: auto-play больше не выбирает жёстко
  `DailyTicketPurchaseService` или `WeeklyTicketPurchaseService`, а использует
  универсальный `LotteryTicketPurchaseService` и стратегию самой лотереи;
- планировщик передаёт в auto-play настроенный `OWNER_TELEGRAM_ID`, поэтому функция
  исполняется только для владельца даже при наличии старых включённых настроек;
- расписание обычных лотерей продублировано в хронологическом виде, а полная
  почасовая таблица FLASH/SHADOW оставлена единым источником точного времени.

Теперь система работает так:

- один и тот же идемпотентный механизм покупает владельцу пять билетов в Weekly,
  Daily, специальных и быстрых лотереях;
- повторный проход планировщика не создаёт дубликаты, а ошибки одной попытки не
  приводят к списанию CAS или частичной покупке.

Технически:

- migration: не требуется;
- Ruff, форматирование и mypy: успешно;
- backend tests: `152 passed`;
- Mini App: typecheck/lint, `31 passed`, production build — успешно;
- Admin Panel: typecheck/lint, `9 passed`, production build — успешно;
- fix commit: `e100f9f`.

## [1.8.1] - 2026-09-01

### Автопокупка владельца и живой переход Fast

Сделано:

- из выборки `AutoPlayService` снято исключение FLASH и SHADOW: существующая
  настройка владельца на пять билетов применяется к каждому открытому Fast-тиражу;
- сохранена идемпотентность по паре пользователь/тираж и источник билета `AUTO_PLAY`,
  поэтому повторный проход планировщика не создаёт второй комплект;
- личный Telegram-результат Fast создаётся только для участника с auto-play билетом;
  обычным игрокам результат продолжает приходить в центр уведомлений Mini App;
- статичный разделитель ближайших FLASH/SHADOW заменён движущимся световым импульсом
  и мягким пульсом центральной молнии; учтён `prefers-reduced-motion`;
- `docs/LOTTERY_SCHEDULE.md` дополнен всеми точными временами FLASH и SHADOW за сутки.

Теперь система работает так:

- владелец автоматически получает пять случайных билетов на каждый из 144 быстрых
  тиражей в сутки без предварительного создания сотен будущих билетов;
- покупка выполняется обычным транзакционным сервисом через ledger и не удваивается
  после перезапуска или повторного запуска планировщика;
- результаты владельца доставляются через существующую надёжную Telegram-очередь.

Технически:

- migration: не требуется;
- Ruff и форматирование: успешно;
- mypy: успешно;
- backend tests: `152 passed`;
- Mini App: typecheck/lint, `31 passed`, production build — успешно;
- Admin Panel: typecheck/lint, `9 passed`, production build — успешно;
- feature commit: `954b45a`.

## [1.8.0] - 2026-09-01

### Fast — чередующиеся FLASH и SHADOW

Сделано:

- зарегистрирована универсальная стратегия `fast_3_15`: билет 888 CAS, выплаты
  88 CAS за 1/3, 888 CAS за 2/3 и раздел jackpot при 3/3;
- миграция `0024_fast_lotteries` создаёт FLASH и SHADOW с отдельными счетами,
  нумерацией с единицы, cutoff одну минуту и двумя подготовленными тиражами;
- интервальные якоря `00:00` и `00:10` дают чередование каждые 10 минут без
  отдельного планировщика;
- покупка и settlement используют существующие транзакционные сервисы, ledger,
  блокировки, ограничения и идемпотентность;
- Fast исключён из обычного live/SSE, Telegram-результатов, jackpot news,
  inactivity reminders и auto-play владельца;
- каждый игрок с Fast-билетом получает итог раунда в Mini App inbox;
- Mini App получил отдельный Fast-раздел, прямой экран выбора сигналов, разные
  FLASH/SHADOW-состояния, адаптивную сетку и компактные WebP-сцены;
- серверная выборка и клиентская очередь исправлены так, чтобы главная брала
  ближайший обычный тираж с ещё открытыми продажами;
- полное расписание закреплено в `docs/LOTTERY_SCHEDULE.md`, устаревшие описания
  финансовой схемы и scheduler приведены к текущей архитектуре.

Теперь система работает так:

- FLASH идёт в `:00/:20/:40`, SHADOW — в `:10/:30/:50` по Москве;
- у каждого Fast-продукта независимы draw number, ticket number, jackpot и
  история, но математика обслуживается одной стратегией;
- пользователь выбирает три позиции и покупает билет напрямую, а результат
  находит в «Моё → Уведомления»;
- обычная главная и «Эфир» остаются спокойными и не заполняются десятками
  быстрых тиражей.

Технически:

- migration: `0024_fast_lotteries`;
- production-совместимость migration: фактическое сокращённое PostgreSQL-имя
  check-constraint определяется динамически;
- Ruff и форматирование: успешно;
- mypy: успешно;
- backend tests: `151 passed`;
- Mini App: typecheck/lint, `31 passed`, production build — успешно;
- Admin Panel: typecheck/lint, `9 passed`, production build — успешно;
- Alembic: одна голова `0024_fast_lotteries`; локальный schema check недоступен
  без локального `DATABASE_URL`, обязательный production check выполняется
  release-скриптом;
- secret scan: успешно, реальный `.env` не отслеживается Git;
- автоматическая browser-проверка недоступна: в сессии не подключён браузер;
  мобильный компонентный сценарий и production build прошли;
- feature commit: `a1dd7e0`.

## [1.7.0] - 2026-09-01

### Единая финансовая схема и события джекпота

Сделано:

- добавлены singleton-счёт Фонда Каспера и неизменяемый реестр сорванных
  джекпотов;
- новые покупки переведены на схему `100% → jackpot`;
- обычные выплаты и восстановление base jackpot переведены на единый фонд с
  обязательными ledger-записями;
- старые остатки distribution/reserve безопасно переносятся миграцией в общий
  фонд, а сами счета остаются в истории;
- конфигурация цены, стратегии, формата и базового джекпота фиксируется в draw
  при его создании;
- добавлено общее `JACKPOT_NEWS` для Mini App без массовой Telegram-рассылки;
- Admin Dashboard получил сводку по фонду, сорванным джекпотам и победителям.

Теперь система работает так:

- добавление новой лотереи не требует отдельной схемы distribution/reserve;
- весь билет увеличивает видимый джекпот конкретной лотереи;
- 2/5, 3/5, Weekly 4/5, Daily 2/4 и 3/4, а также фиксированные выигрыши
  специальных лотерей оплачиваются из одного Фонда Каспера;
- при главном выигрыше победители делят jackpot, после чего фонд восстанавливает
  значение, сохранённое в конфигурации этого тиража;
- все игроки видят новость о сорванном джекпоте в Mini App, а победитель также
  получает своё обычное личное уведомление.

Технически:

- migrations: `0022_kasper_fund`, `0023_kasper_constraints`;
- production-совместимость migration: фактические сокращённые PostgreSQL-имена
  старых check-constraints определяются динамически, а завершённые тиражи не
  затрагиваются при заполнении snapshot;
- Ruff и форматирование: успешно;
- mypy: успешно;
- backend tests: `148 passed`;
- Mini App: typecheck/lint, `31 passed`, production build — успешно;
- Admin Panel: typecheck/lint, `9 passed`, production build — успешно;
- secret scan: успешно, `.env` не отслеживается Git;
- feature commit: `8d8f2f7`; migration fixes: `f6cb650`, `140d47e`, `134a7f3`.

## [1.6.0] - 2026-09-01

### Ежедневная лотерея «ГРОБ» 3/16

Сделано:

- зарегистрирована универсальная стратегия `grob_3_16`;
- добавлена ledger-safe миграция `0021_grob_lottery` с отдельными фондами и
  нумерацией тиражей/билетов с единицы;
- настроены ежедневные слоты 06:06 и 23:06 по Москве с cutoff две минуты;
- реализованы фиксированные выплаты 666/6 666 CAS, reserve fallback, перенос
  фондов, раздел jackpot и его сброс к базовому значению;
- Admin Panel автоматически получила новую лотерею во всех общих выборках,
  аналитике, тиражах и настройках;
- Mini App получил отдельные home, picker и live-состояния, готическую сетку
  4×4, анимацию «запечатывания» выбранного числа и оптимизированную WebP-сцену;
- сохранена фраза «На том свете джекпоты больше…».

Теперь система работает так:

- «ГРОБ» существует как самостоятельный продукт и не делит номера или фонды
  с другими Daily-лотереями;
- один билет всегда направляет 2 666 CAS в jackpot и 4 000 CAS в distribution;
- результат финансового распределения не зависит от размера корзины;
- тиражи отображаются как `RIP 0001`, билеты — как `Могила 0001`, внутренние
  идентификаторы и общая архитектура не изменены.

Технически:

- migration: `0021_grob_lottery`;
- проверки: Ruff и форматирование — успешно, mypy — успешно, backend
  `148 passed`, Mini App `31 passed`, Admin Panel `9 passed`, обе production-сборки — успешно;
- secret scan: успешно, `.env` не отслеживается Git;
- автоматический browser screenshot недоступен: в среде не подключён браузер;
  компонентный мобильный сценарий и production build прошли;
- release commit: `30393df`.

## [1.5.0] - 2026-09-01

### Оперативный штаб владельца и непрерывный сценарий покупки

Сделано:

- добавлено подтверждение успешной покупки без принудительного перехода в «Моё»;
- на главную Admin Panel подключена существующая агрегированная аналитика билетов;
- реализована общая сводка за всё время и компактное отображение крупных сумм CAS;
- добавлен лёгкий read-only отчёт статистики чисел с метаданными периода;
- доступны окна «Все», 10, 20, 50 и 100 тиражей;
- аналитика по лотереям дополнена фактической долей выигрышей, оценкой сложности и возвратом;
- Admin Panel получила самостоятельную стилистику закрытого оперативного пространства;
- `docs/NEXT_STEPS.md` переписан под фактическое состояние готового частного проекта.

Теперь система работает так:

- после оплаты игрок выбирает, купить ещё билет или открыть свои билеты;
- владелец при входе сразу видит главные показатели всей игры;
- историю лотерей можно сравнивать по выигрышам и выплатам без тяжёлой загрузки отдельных билетов;
- статистика чисел считает только выбранное окно нового аналитического периода, а исходные
  завершённые тиражи остаются неизменяемыми.

Технически:

- migration: не требуется;
- аналитика билетов использует два агрегатных SQL-запроса и кэш до 60 секунд;
- статистика чисел читает только выигрышные комбинации выбранной лотереи;
- проверки: Ruff и форматирование — успешно, mypy — успешно, backend Admin/health
  `18 passed`, Mini App `30 passed`, Admin Panel `9 passed`, обе production-сборки — успешно;
- release commit: `f0ba298`.

## [1.4.2] - 2026-09-01

### Ближайший тираж и переключение на одном экране

Сделано:

- восстановлен приоритет карточки ближайшего тиража на главной;
- лента переключения перенесена под карточку без дополнительных заголовков;
- только для главной уменьшены высота сцены, интервалы, блок времени и кнопки;
- добавлена отдельная компактная компоновка для невысоких экранов.

Теперь система работает так:

- при входе игрок сразу видит ближайшую лотерею и может перейти к выбору чисел;
- следующую лотерею можно выбрать в расположенной ниже ленте без лишней прокрутки;
- экран покупки и его компактное поле чисел не изменились.

Технически:

- migration: не требуется;
- затронут только интерфейс Mini App;
- проверки: ESLint — успешно, TypeScript — успешно, Mini App `30 passed`, production build — успешно,
  metadata/health `4 passed`;
- release commit: `46a025f`.

## [1.4.1] - 2026-09-01

### Компактный игровой экран без лишней прокрутки

Сделано:

- удалён слоган, занимавший первый экран главной;
- лента переключения лотерей перенесена перед выбранным тиражом и получила
  явную подпись действия;
- большая иллюстрация picker преобразована в компактную анимированную шапку;
- название лотереи и инструкция размещены поверх защищённой затемнённой части
  сцены;
- поле комбинации, стоимость и выбранные числа подняты ближе к верхней границе;
- wordmark «Каспер» собран в одну поверхность без визуального разрыва между
  первой буквой и продолжением слова.

Теперь система работает так:

- пользователь сразу видит, что лотереи можно переключать;
- после открытия покупки игровое поле начинается на первом экране телефона;
- атмосферная графика остаётся живой, но больше не конкурирует с главным
  действием — выбором чисел.

Технически:

- migration: не требуется;
- проверки: Ruff и форматирование — успешно, mypy — успешно, backend
  `144 passed`, Mini App `30 passed`, Admin Panel `8 passed`, обе production
  frontend-сборки — успешно;
- release commit: `ffe33e5`.

## [1.4.0] - 2026-09-01

### Кинематографичная визуальная система Mini App

Сделано:

- карточная надстройка заменена отдельным иллюстрированным продуктовым слоем;
- для ПЛЛ, ПСС, ХАН и Weekly подготовлены оптимизированные WebP-сцены, а
  «3 СЕНТЯБРЯ» сохранила собственную осеннюю SVG-композицию;
- статичные изображения разделены на дальний и передний планы с независимым
  движением камеры, светом, туманом, зерном и эффектами среды;
- переключатель лотерей собран как единая лента расписания без повторяющихся
  карточек;
- главная, пять вариантов выбора чисел, эфир, «Моё» и корзина перестроены на
  новой визуальной иерархии;
- исправлен конфликт старой пятиколоночной сетки с новыми композициями picker;
- добавлен безопасный browser-only режим дизайн-превью без Telegram и базы.

Теперь система работает так:

- каждая лотерея узнаётся по собственному месту, свету, движению и геометрии,
  а не только по цвету фона;
- сцены выглядят живыми без видео и постоянной нагрузки на сервер: анимация
  выполняется на устройстве, а изображения загружаются только как статические
  оптимизированные ресурсы;
- иллюстрация физически отделена от игровых данных и не пересекает название,
  время, jackpot или кнопки;
- при системном ограничении движения параллакс и атмосферные эффекты
  отключаются автоматически.

Технически:

- migration: не требуется;
- зависимости: `motion` для переходов и многослойной анимации;
- графика: четыре WebP-файла размером 30–63 КБ;
- проверки: Ruff и форматирование — успешно, mypy — успешно, backend
  `144 passed`, Mini App `30 passed`, Admin Panel `8 passed`, обе production
  frontend-сборки — успешно; локальный Alembic check недоступен без
  `DATABASE_URL` и выполняется release-сценарием на VPS;
- release commit: `9ac985f`.

## [1.3.0] - 2026-09-01

### K-Loto Design 2.0

Сделано:

- визуальная система Mini App собрана вокруг двух фирменных мотивов: времени
  `2:22` и тонкой координатной геометрии;
- wordmark, ближайший тираж, переключатель лотерей, выбор чисел, билеты и
  нижняя навигация получили единый характер без тяжёлых зависимостей;
- эфир дополнен медленно движущимися числовыми слоями, линиями, более активным
  состоянием проведения тиража и отдельной композицией результата;
- «3 СЕНТЯБРЯ» получила расширенную календарную тему с собственной типографикой,
  терракотово-бордовой сценой и эффектом рукописной отметки выбранного числа;
- добавлена регрессионная проверка отдельного формата эфира 3 из 33.

Теперь система работает так:

- K-Loto узнаётся по форме, линиям и мотиву `2:22`, а не только по цветам и
  названию;
- каждая лотерея сохраняет общий интерфейс, но имеет собственный цветовой знак;
- эфир остаётся лёгким CSS/SVG-интерфейсом и визуально оживает без видео, 3D,
  canvas и постоянных тяжёлых эффектов;
- при отключённых системных анимациях все новые движения автоматически
  сокращаются почти до нуля.

Технически:

- migration: не требуется;
- зависимости: новые пакеты не добавлялись;
- проверки: Mini App lint и typecheck — успешно, `30 passed`, production build
  — успешно; проверка версии и health API — `4 passed`;
- release commit: `547d0b1`.

## [1.2.1] - 2026-09-01

### Исправление стартовой нумерации «3 СЕНТЯБРЯ»

Сделано:

- production проверен до изменения: билетов и завершённых тиражей новой
  лотереи не было;
- два пустых запланированных тиража перенумерованы из №53/№54 в №1/№2;
- следующий тираж получил счётчик №3, а первый будущий билет — №1;
- миграция прерывается без изменений, если успел появиться хотя бы один билет
  или начался хотя бы один тираж.

Теперь система работает так:

- «3 СЕНТЯБРЯ» имеет полностью самостоятельные номера тиражей и билетов с
  единицы;
- история, ledger и фонды остальных лотерей не меняются.

Технически:

- migration: `0020_september_numbering`;
- проверки: Ruff и форматирование — успешно, mypy — успешно, backend
  `144 passed`, Mini App `29 passed`, Admin Panel `8 passed`, production-сборки
  — успешно;
- release commit: `6d289f3`.

## [1.2.0] - 2026-09-01

### Новая ежедневная лотерея «3 СЕНТЯБРЯ» 3/33

Сделано:

- в универсальную стратегию добавлены фиксированные выплаты и управляемое
  восстановление главного приза из reserve;
- миграция создаёт самостоятельную активную лотерею, два ежедневных слота,
  отдельные счётчики, jackpot, distribution и reserve;
- стоимость каждого билета целиком поступает в distribution, а нулевая доля
  jackpot больше не создаёт недопустимую нулевую ledger-запись;
- главный приз делится между всеми билетами 3/3 с детерминированным
  распределением остатка в 1 CAS;
- Mini App получил отдельную осеннюю тему выбранного тиража и календарную сетку
  выбора 3 чисел из 33 без новых библиотек и тяжёлой графики;
- в редактируемые тексты добавлен отдельный раздел «3 СЕНТЯБРЯ».

Теперь система работает так:

- тиражи «3 СЕНТЯБРЯ» проходят ежедневно в 03:33 и 15:33 МСК с cutoff две
  минуты и используют общие scheduler, recovery, purchase, live и notification
  механизмы;
- выплаты 1/3 и 2/3 равны 333 и 3 333 CAS, а общий приз 33 333 333 CAS делится
  между победителями 3/3 и восстанавливается из резерва;
- новая лотерея автоматически появляется в Mini App, эфире, истории,
  уведомлениях и Admin Panel.

Технически:

- migration: `0019_september_lottery`;
- ruleset: `september_3_33`;
- стартовый reserve: `1 000 000 000 CAS`;
- проверки: Ruff и форматирование — успешно, mypy — успешно, backend
  `144 passed`, Mini App `29 passed`, Admin Panel `8 passed`, обе production
  frontend-сборки — успешно;
- release commit: `3e997e1`.

## [1.1.0] - 2026-09-01

### Универсальное игровое ядро и короткая проверка надёжности

Сделано:

- математика Weekly 5/20 и Daily 4/15 переведена на декларативный реестр `LotteryRuleStrategy` без изменения действующих выплат;
- сущность лотереи получила версионируемую ссылку `ruleset_code`, а покупка и settlement перестали выбирать обработчик по жёстко заданному коду;
- scheduler получил стратегию интервальных тиражей и настраиваемое количество подготовленных будущих тиражей;
- исправлена вложенная транзакция, из-за которой не сохранялись избранные комбинации;
- клиент показывает состояние «Комбинация сохранена», сохраняет корзину в текущей вкладке и обнаруживает новую серверную версию;
- production backup скачан вне VPS, проверен по формату и SHA-256; добавлены повторяемые скрипты backup и одноразового PostgreSQL smoke;
- документация SSE, лимитов и процесса добавления лотереи снова соответствует коду.

Теперь система работает так:

- новый формат добавляется одной чистой стратегией, миграцией сущности и тестами, без дублирования API, ledger и scheduler-логики;
- открытый во время релиза Mini App продолжает текущую сессию, затем предлагает явное обновление без потери корзины вкладки;
- нагрузочная проверка не изменяет production: она использует временную PostgreSQL-базу и удаляет её после выполнения.

Технически:

- migration: `0018_lottery_rulesets`;
- проверки: backend `139 passed`, Mini App `29 passed`, Admin Panel `8 passed`;
- PostgreSQL smoke: 50 dashboard-запросов — `2.611 s`, покупка 5 000 билетов — `2.797 s`, settlement — `3.981 s`;
- production: `alembic check` — расхождений нет, восстановление свежей копии — успешно, API — healthy;
- внешняя копия: PostgreSQL dump проверен локально и исключён из Git;
- внешний мониторинг: активированы две независимые проверки UptimeRobot для Mini App и `/health` с уведомлениями владельца;
- Telegram: владелец подтвердил корректную работу разрешений и доставки на трёх реальных аккаунтах;
- commits: `00d96b2` (релиз), `bd07c30` (изолированный smoke на восстановленной копии).

## [1.0.2] - 2026-09-01

### Фирменное оформление названия «Каспер»

Сделано:

- wordmark собран в единую композицию из золотого знака и синей текстовой
  поверхности;
- усилены типографика, контраст, глубина, мягкая тень и золотое отражение;
- знак получил тонкую светлую окантовку и небольшой фирменный наклон;
- добавлена отдельная компактная геометрия для экранов уже 360 px.

Теперь система работает так:

- название в шапке воспринимается как самостоятельный бренд, а не как обычная
  подпись рядом со значком;
- wordmark сохраняет читаемость и не мешает балансу на маленьких телефонах.

Технически:

- изменён только responsive CSS Mini App и метаданные PATCH-релиза;
- schema migration и backend domain-тесты не требуются;
- выполнены целевые проверки Mini App и production build.

## [1.0.1] - 2026-09-01

### Единый логотип «Каспер»

Сделано:

- текстовая часть wordmark изменена с полного имени на продолжение «аспер»;
- дизайнерская «К» и текстовое продолжение теперь образуют одно слово без
  визуального повторения первой буквы;
- для вспомогательных технологий сохранено полное доступное имя «Каспер»;
- добавлен UI regression-тест итогового текста wordmark.

Теперь система работает так:

- в шапке Mini App читается «Каспер», а не «К Каспер»;
- владелец по-прежнему может редактировать продолжение названия в общем файле
  текстов, где добавлено пояснение о дизайнерской первой букве.

Технически:

- schema migration не требуется;
- изменение затрагивает только Mini App и метаданные PATCH-релиза;
- проверки: Ruff и форматирование без замечаний, mypy без ошибок, backend
  `137 passed`, Mini App `30 passed`, Admin Panel `8 passed`; оба интерфейса
  прошли typecheck, lint и production build;
- production deployment выполняется после фиксации release commit.

## [1.0.0] - 2026-09-01

### Стабильная нумерация, навигация Admin Panel и аналитика билетов

Сделано:

- внутреннее состояние Admin Panel синхронизировано с History API и
  `localStorage`; прямые URL `/players`, `/ticket-analytics`, `/development` и
  остальные восстанавливаются после обновления и поддерживают кнопки
  «Назад»/«Вперёд» браузера;
- добавлен read-only endpoint аналитики билетов и новый экран со сводными и
  раздельными показателями по лотереям;
- агрегаты вычисляются в PostgreSQL без загрузки отдельных билетов в память и
  кэшируются на 60 секунд в каждом API worker;
- API журнала разработки присваивает записям отдельную последовательность
  `DEV-0001`, сохраняя исходные Markdown-файлы и версии релизов;
- CHANGELOG и DEVLOG получили разные пояснения и назначение в интерфейсе.

Теперь система работает так:

- владелец остаётся в выбранном разделе Admin Panel после обновления страницы;
- долю выигрышных билетов, продажи и выплаты можно посмотреть по всей системе
  и по каждой лотерее отдельно;
- номер релиза отвечает на вопрос «какая версия продукта», а номер DEV —
  «какая по счёту техническая запись».

Технически:

- schema migration не требуется;
- добавлены regression-тесты маршрутизации, представления журналов и SQL-
  агрегатов аналитики;
- версия `1.0.0` фиксирует переход стабильного работающего проекта с ветки
  разработки `0.x`; старые записи не переписаны;
- проверки: Ruff и форматирование без замечаний, mypy без ошибок, backend
  `137 passed`, Mini App `30 passed`, Admin Panel `8 passed`; оба интерфейса
  прошли typecheck, lint и production build.

Развёртывание:

- release commit: `1a2a0b6`;
- API и gateway v1.0.0 развёрнуты на VPS, не изменявшийся Telegram-бот не
  перезапускался;
- production `alembic check` чистый, резервная копия восстановлена во временную
  БД: 5 пользователей, 56 тиражей, 1 072 билета и 462 ledger-записи;
- health, главная Admin Panel и прямые адреса `/ticket-analytics` и
  `/development` отвечают `200` по HTTPS.

## [0.23.1] - 2026-09-01

### Упрощение профиля, тексты Каспера и надёжный прямой эфир

Сделано:

- удалены два отдельных переключателя категорий уведомлений; единая кнопка
  включает или отключает обе согласованные категории;
- шапка показывает кириллическую «К» в золотом квадрате и имя «Каспер» без
  подписи «Цифровая лотерея»;
- на главной и в разделе «Моё» применены согласованные владельцем тексты;
- статистика дополнена активными билетами и процентом выигрышных билетов,
  вычисляемым из уже загруженного account response;
- presentation timeline завершённого тиража привязана к `executed_at`, если
  settlement закончился позднее `scheduled_at`; RNG и результат не меняются;
- `content.ts` разделён по экранам, а `publish_miniapp_texts.ps1` проверяет,
  фиксирует и публикует только безопасное изменение этого файла.

Теперь система работает так:

- игрок видит одно действие для уведомлений вместо набора технических опций;
- во время реального эфира готовый результат показывается последовательно,
  даже если scheduler получил его через несколько секунд после времени тиража;
- владелец может менять основные подписи в VS Code и публиковать их одной
  командой, не смешивая с другими изменениями проекта.

Технически:

- schema migration не требуется;
- добавлен regression-тест поздней готовности результата и UI-тест единственной
  кнопки уведомлений;
- проверки: Ruff, mypy и backend `135 passed`; Mini App typecheck/lint/build и
  `30 passed`; Admin typecheck/lint/build и `6 passed`;
- production Alembic check, backup restore и health выполняются единым
  release-скриптом после commit.

Развёртывание:

- release commit: `a879553`;
- v0.23.1 развёрнута для API и gateway; PostgreSQL healthy, bot продолжил
  работать без лишнего перезапуска;
- production `alembic check` чистый, backup восстановлен во временную БД:
  5 пользователей, 56 тиражей, 1 072 билета и 462 ledger-записи;
- HTTPS health отвечает `200`; опубликованный bundle содержит все новые фразы,
  а старые «Цифровая лотерея», «Личное пространство» и «Сервер готовит
  результат» отсутствуют.

## [0.23.0] - 2026-09-01

### Эксплуатационная надёжность и упрощение сопровождения

Сделано:

- правила проекта разделяют быстрые проверки текста/CSS, проверки отдельного
  интерфейса и полный контур для денег, БД, расписания и релиза;
- основные изменяемые надписи вынесены в `frontend/miniapp/src/content.ts`, где
  владельцу оставлена пошаговая инструкция; данные лотерей по-прежнему меняются
  в Admin Panel;
- сведения об автоучастии исключены из публичного account API, TypeScript-типа
  и профиля Mini App, не меняя закрытую настройку и созданные билеты владельца;
- добавлен пользовательский endpoint и кнопка проверки Telegram-доставки с
  часовым idempotency key;
- планировщик контролирует зависшие DRAWING/SETTLING и очередь уведомлений,
  отправляет владельцу редактированное системное сообщение не чаще раза в час;
- бот сокращён до `/start`, `/menu`, `/web`, постоянной кнопки Mini App и
  outbox-worker; удалены старые обработчики покупки и их дублирующий UI-код;
- три исторических `TICKET_PURCHASED` без Telegram identity переводятся
  миграцией в `CANCELLED` вместо бесконечного повтора;
- добавлены `load_test_core.py`, `verify_backup_restore.sh`, `.dockerignore` и
  единый `release_vps.py` с обязательной копией БД перед выпуском.

Теперь система работает так:

- игроки не видят эксклюзивную функцию владельца;
- разрешение Telegram можно проверить реальным сообщением на каждом аккаунте;
- зависшие операции автоматически повторяются существующим outbox/recovery, а
  накопившаяся проблема становится видна владельцу;
- один выпуск выполняет backup, загрузку текущего commit, сборку выбранных
  сервисов, миграцию и вывод их состояния.

Технически:

- migrations: `0016_operational_notifications`, `0017_cancel_legacy_notices`;
- нагрузочная проба: 5 000 билетов, bulk validation 0,04 с, Daily settlement
  0,07 с, Weekly settlement 0,09 с на локальной машине;
- проверки: Ruff и mypy пройдены; backend `134 passed`; Mini App
  typecheck/lint/build и `29 passed`; Admin typecheck/lint/build и `6 passed`;
- Telegram DevLog отключён; этот русский журнал доступен в Admin Panel.

Развёртывание:

- release commit: `278e799` (основная реализация `65a8eb1`);
- production migrations применены до `0017_cancel_legacy_notices`, `alembic
  check` не обнаружил расхождений;
- свежий dump дважды восстановлен в одноразовую БД: 5 пользователей, 56
  тиражей, 1 072 билета и 462 ledger-записи; рабочая база не изменялась;
- API/PostgreSQL healthy, bot/gateway запущены, Mini App, Admin Panel и health
  endpoint отвечают `200`;
- планировщик без ошибки, зависших тиражей нет; 117 уведомлений доставлено,
  три недоставимых исторических сообщения корректно отменены.

## [0.22.0] - 2026-09-01

### Личный кабинет, согласие на уведомления и автоучастие

Сделано:

- вкладка «Моё» объединила обзор игрока, статистику, билеты, фильтры истории,
  внутренние уведомления и настройки сообщений бота;
- после первой успешной покупки Mini App предлагает нативно разрешить боту
  писать пользователю, а решение можно позднее изменить в личном кабинете;
- settlement формирует сообщение бота только участникам конкретного тиража с
  включённой категорией результатов; рассылка неучастникам удалена;
- планировщик создаёт не чаще одного раза в 24 часа приглашение для игрока без
  свежей покупки и отправляет его в Telegram только при отдельном разрешении;
- добавлен серверный AutoPlayService: для включённого игрока он покупает пять
  криптографически случайных билетов на каждый открытый тираж;
- источник билета сохраняется как MANUAL или AUTO_PLAY, поэтому автопокупку
  можно отличить, проверить и безопасно повторить после перезапуска;
- в Admin Panel существующая карточка игрока дополнена статическим управлением
  автоучастием с обязательной причиной и записью AdminAuditLog.

Теперь система работает так:

- бот не дублирует каждую покупку и не рассылает результаты посторонних
  тиражей;
- пользователь сам разрешает два понятных типа сообщений: результат своего
  тиража и спокойное напоминание после суток без покупки;
- выигрыши и приглашения сохраняются внутри Mini App, доступны после повторного
  открытия и отмечаются прочитанными отдельно от Telegram;
- пять автобилетов владельца создаются обычной финансовой операцией с теми же
  балансом, лимитами, фондами и ledger, что и ручная покупка;
- повторный цикл планировщика не создаёт второй набор автобилетов для того же
  игрока и тиража.

Технически:

- migrations: `0014_player_inbox_auto_play`,
  `0015_normalize_auto_play_constraint`;
- API: `GET /api/v1/miniapp/account`, inbox и notification-preferences,
  `PUT /api/v1/admin/players/{user_id}/auto-play`;
- зависимости: новые runtime-библиотеки не добавлялись;
- проверки: Ruff, mypy и backend `143 passed`; Mini App `29 passed`; Admin
  `6 passed`; production builds, Alembic check и secret scan выполняются перед
  deployment;
- Telegram DevLog остаётся отключённым; журналы на русском доступны в Admin
  Panel;
- коммиты: реализация `75ad126`, документация `53d8d1a`, совместимость
  production-схемы `88dc3e7`, `6a8a6d4`, `512cc46`.

Развёртывание:

- перед изменением схемы создана резервная копия
  `k-loto-20260831T234054Z.dump`;
- v0.22.0 развёрнута на VPS, миграции применены до
  `0015_normalize_auto_play_ck`, production `alembic check` не обнаружил
  расхождений;
- API и PostgreSQL healthy, bot и gateway запущены, Mini App, Admin Panel и
  `/health` отвечают по HTTPS с кодом `200`;
- для Telegram ID владельца включено пять автобилетов на каждый тираж через
  аудируемый AdminMutationService; создано по пять билетов для четырёх текущих
  открытых тиражей, ошибок автоучастия и планировщика нет.

## [0.21.0] - 2026-09-01

### Мультитираж, серверный эфир и оперативный пульт владельца

Сделано:

- сервис покупки принимает 1 или 5 тиражей, подготавливает недостающие будущие
  тиражи под блокировкой лотереи и создаёт все билеты одной транзакцией;
- полная цена мультитиража списывается один раз и сразу отражается тремя
  согласованными ledger-записями пользователя, jackpot и distribution;
- предел одной покупки увеличен с 100 до 1000 комбинаций, добавлен серверный
  лимит 5000 билетов пользователя на тираж и ограничитель частоты запросов;
- клиент больше не дробит крупную корзину на несколько покупок;
- сервер формирует начало эфира, моменты появления чисел и окончание, а новый
  SSE endpoint передаёт персональные снимки без WebSocket;
- Mini App восстанавливает эфир по серверному времени, показывает жизненный
  цикл продаж и продолжает автоматически получать следующий тираж;
- существующий сервис избранного подключён к Mini App; добавлены фильтры истории,
  выбор 100 случайных комбинаций и месячная сумма выплат без бегущей строки;
- heartbeat планировщика сохраняется в БД после успеха и ошибки;
- Admin Panel получила статичный оперативный пульт, поиск игрока, очередь
  уведомлений и управление cutoff и лимитами; запросы выполняются только при
  открытии владельцем и не влияют на пользовательский трафик.

Теперь система работает так:

- режим 5 тиражей выключен по умолчанию и не мешает обычной покупке;
- при выборе пяти тиражей игрок заранее видит сумму и не получает скрытых
  последующих списаний или автопродления;
- закрытие и повторное открытие Mini App не перезапускает визуальный розыгрыш:
  пользователь сразу видит актуальное число или результат;
- до 1000 комбинаций одной лотереи отправляются одной идемпотентной операцией;
- владелец видит последнюю успешную проверку планировщика, зависшие тиражи,
  участников, билеты, продажи и состояние доставки уведомлений.

Технически:

- migrations: `0011_operational_limits`, `0012_scheduler_heartbeat`,
  `0013_normalize_limit_constraints`;
- API: `GET /api/v1/miniapp/live/stream`, favorites API, фильтры tickets,
  расширенная bulk/multi-draw purchase и `GET /api/v1/admin/notifications`;
- зависимости: новые runtime-библиотеки не добавлялись;
- проверки перед релизом: Ruff, mypy и backend `140 passed`; Mini App
  `29 passed`; Admin `6 passed`; оба production build, Alembic check и secret
  scan выполняются перед deployment;
- Telegram DevLog отключён по принятому решению; русские журналы доступны в
  защищённой Admin Panel.

Развёртывание:

- резервная копия `k-loto-20260831T224854Z.dump` проверена перед изменением схемы;
- v0.21.0 развёрнута на VPS, миграции применены до
  `0013_normalize_limit_constraints`, production `alembic check` не обнаружил
  расхождений;
- API и PostgreSQL healthy, heartbeat планировщика обновляется, бот и gateway
  запущены без ошибок старта;
- Mini App и Admin Panel отвечают по HTTPS с кодом `200`, защищённый SSE endpoint
  без Telegram-авторизации корректно отвечает `401`;
- коммиты реализации: `07088fc`, `f6fc61e`; документация: `3c33aa0`;
  исправление имён ограничений production-схемы: `496cb4f`.

## [0.20.0] - 2026-09-01

### Сфокусированный игровой интерфейс и цифровой архив эфиров

Сделано:

- главная страница перестроена вокруг одного активного продуктового блока;
  остальные лотереи переключаются компактной строкой расписания;
- добавлены отдельные визуальные токены ПЛЛ, ПСС, ХАН и Weekly, которые
  применяются на главной, в выборе чисел, эфире, повторах, билетах и корзине;
- экран покупки дополнен живым предварительным билетом, сохранив скруглённые
  числовые клавиши, быстрые случайные комбинации и пакетную корзину;
- активные и завершённые билеты группируются по тиражам, а крупная корзина — по
  лотереям и показывает только ограниченное превью комбинаций;
- read-only API эфира расширен двумя последними завершёнными тиражами каждой
  лотереи и персональным итогом пользователя;
- реализован цифровой повтор сохранённой последовательности чисел с отдельной
  маркировкой, спокойной визуальной сценой, повторным запуском и возвратом к
  актуальному эфиру;
- стандартные иконки навигации заменены на собственные линейные знаки K-Loto;
- Admin Panel получила фирменную navy/blue/burgundy/gold оболочку и остаётся
  полностью статичной, без animations и transitions.

Теперь система работает так:

- пользователь видит один главный тираж, быстро переключает расписание и не
  прокручивает стену однотипных карточек;
- покупка каждой лотереи визуально узнаваема, но расположение элементов и
  правила действий остаются одинаковыми;
- вкладка «Эфир» полезна между розыгрышами: в ней доступны цифровые повторы
  последних двух тиражей каждой лотереи;
- повтор не имитирует новый выбор чисел: клиент воспроизводит только ранее
  сохранённый неизменяемый результат;
- крупные наборы билетов не создают тысячи тяжёлых карточек на экране.

Технически:

- migration: изменений схемы после `0010_independent_daily` нет;
- API: `MiniAppLiveFeed.recent_completed` содержит до двух тиражей каждой
  лотереи из ограниченной выборки последних завершённых тиражей; сохранённые
  старые Daily-тиражи отображаются под своей публичной ПЛЛ/ПСС/ХАН-сущностью;
- зависимости: новые runtime-библиотеки не добавлялись;
- игровая логика: RNG, scheduler, settlement и ledger-правила не изменялись;
- проверки: Ruff и форматирование — пройдены; mypy — пройден; backend —
  `137 passed`; Mini App — `28 passed`; Admin — `6 passed`; оба production
  build — собраны; Alembic single-head, production `alembic check` и secret
  scan — пройдены;
- deployment: backup `k-loto-20260831T213310Z.dump` проверен; v0.20.0
  развёрнута на VPS; API, PostgreSQL, bot и gateway работают, оба HTTPS-сайта
  отвечают `200`, ошибок запуска API/bot не обнаружено;
- коммит реализации: `05b7b44`.

## [0.19.0] - 2026-08-31

### Надёжная покупка и развитие главной страницы и эфира

Сделано:

- production-диагностика подтвердила, что будущие Weekly, ПСС и ХАН были
  открыты, а ложное закрытие возникало на уровне устаревшего клиентского
  dashboard;
- dashboard получил серверное время и количество билетов пользователя для
  каждого ближайшего тиража;
- добавлено обновление каждые 15 секунд, при возврате из фона и непосредственно
  перед открытием выбора чисел; GET-запросы исключены из браузерного кеша;
- добавлены серверный предел 100 билетов на одну транзакционную покупку и
  клиентская корзина до 1000 билетов;
- крупная покупка выполняется пакетами с отдельной идемпотентностью, одним
  безопасным повтором при временном сетевом сбое и сохранением остатка;
- главный экран перестроен вокруг ближайшего тиража, быстрых действий и более
  компактной коллекции лотерей;
- ожидание эфира дополнено линией сигнала, ячейками результата, последней
  минутой и анимацией закрепления раскрытого числа.

Теперь система работает так:

- пользователь всегда получает свежую проверку продаж перед выбором чисел;
- можно быстро добавить 5, 10, 25 или 50 случайных комбинаций и собрать корзину
  вплоть до 1000 билетов;
- при большой покупке виден прогресс, купленные пакеты сразу фиксируются, а
  непроданные остаются в корзине;
- эфир выглядит живым задолго до старта, но не показывает вымышленные числа и
  не меняет серверную игровую логику.

Технически:

- migration: схема базы данных не менялась после `0010_independent_daily`;
- игровая логика: RNG, settlement, scheduler и ledger-правила не изменялись;
- проверки: Ruff и форматирование — пройдены; mypy — пройден; backend —
  `136 passed`; Mini App — `25 passed`; Admin — `6 passed`; оба production
  build — собраны; Alembic head/offline upgrade и secret scan — пройдены;
- deployment: выполняется автоматически после итоговых проверок и backup;
- коммит: зафиксирован коммитом релиза.

## [0.18.0] - 2026-08-31

### Синхронный цифровой эфир тиража

Сделано:

- добавлен аутентифицированный read-only API эфира с серверным временем,
  последним завершённым и ближайшим запланированным тиражами;
- личные данные ограничены агрегатами и тремя наиболее важными билетами, чтобы
  ответ оставался компактным даже при тысячах билетов пользователя;
- реализованы состояния ожидания, старта, последовательного раскрытия чисел,
  персонального результата и следующего тиража;
- добавлены повторная синхронизация после возврата из фона, polling только на
  открытом экране и одна лёгкая тактильная отдача при старте;
- добавлена четвёртая вкладка навигации и контекстная кнопка эфира на главной;
- покрыты тестами фазы по серверному времени, позднее подключение, отсутствие
  билетов, проигрыш, выигрыш, mobile layout и безопасная зона.

Теперь система работает так:

- backend по-прежнему один раз надёжно выбирает и сохраняет результат, а Mini
  App только визуально раскрывает уже неизменяемые числа;
- пользователь может открыть эфир заранее или в середине тиража и увидеть
  актуальный этап без искусственного повтора;
- после финального числа показывается личный результат и ближайший следующий
  тираж с переходами к покупке и билетам;
- визуальный слой использует спокойную сетку и один размытый glow, без видео,
  шаров, звука, WebSocket, WebGL и тяжёлых библиотек.

Технически:

- migration: схема базы данных не менялась после `0010_independent_daily`;
- игровая логика: RNG, scheduler, settlement и recovery не изменялись;
- проверки: Ruff и форматирование — пройдены; mypy — пройден; backend —
  `134 passed`; Mini App — `21 passed`; Admin — `6 passed`; оба production
  build — собраны; Alembic head/offline upgrade и secret scan — пройдены;
- коммит: зафиксирован коммитом релиза.

## [0.17.0] - 2026-08-31

### Полноценный UI/UX-редизайн Mini App

Сделано:

- создана переиспользуемая система компонентов для баланса, кнопок, чисел,
  статусов, пустых состояний, иконок и skeleton-загрузки;
- введены единые дизайн-токены поверхностей, текста, границ, радиусов,
  отступов, длительности и характера анимаций;
- главный экран получил компактный заголовок, ближайший тираж и самостоятельные
  продуктовые карточки четырёх лотерей;
- переработаны выбор чисел, билеты, результаты, корзина и нижняя навигация;
- добавлены анимации выбора числа, баланса, покупки, выигрыша, карточек, вкладок,
  навигации и переходов между страницами;
- добавлена необязательная тактильная отдача через Telegram HapticFeedback;
- исправлен локальный Windows-helper генерации безопасного dev-секрета.

Теперь система работает так:

- интерфейс сохраняет тёмную сине-бордово-золотую эстетику, но имеет отчётливые
  уровни глубины и визуальную иерархию;
- золото обозначает деньги, выигрыш и основные действия, а проигрыш остаётся
  спокойным и нейтральным;
- все существующие покупки, корзина, активные билеты и история используют те же
  серверные API и правила;
- на экранах от 320 пикселей контент не перекрывается нижней навигацией и
  учитывает безопасную зону iPhone.

Технически:

- миграция: изменений схемы после `0010_independent_daily` нет;
- зависимости: новые runtime-библиотеки не добавлялись;
- проверки: зафиксированы итоговой проверкой релиза;
- коммит: зафиксирован коммитом релиза.

## [0.16.1] - 2026-08-31

### Production journal path fix

Сделано:

- corrected release-journal discovery to use the backend process working
  directory in both source and installed-container environments;
- added a regression test that changes the process directory and loads both
  allowed journals.

Теперь система работает так:

- authenticated Admin users can open both complete journal tabs in production.

Технически:

- migration: no schema change after `0010_independent_daily`;
- tests: 133 backend passed after the correction;
- commit: recorded by the patch release commit.

## [0.16.0] - 2026-08-31

### Admin project journals

Сделано:

- added authenticated, read-only Admin API access to the versioned
  `CHANGELOG.md` and `DEVLOG.md` sources;
- added a **Development** Admin section with separate CHANGELOG and DEVLOG tabs;
- included all historical version sections without copying or rewriting them;
- removed Telegram journal discovery/sending scripts and public configuration
  placeholders.

Теперь система работает так:

- the owner reads product and technical history in the permanent Admin site;
- journal content remains version-controlled and cannot be edited through the
  browser;
- Telegram is used only for the player bot and lottery notifications, not
  development reports.

Технически:

- migration: no schema change after `0010_independent_daily`;
- security: fixed journal allowlist, authenticated endpoint and text-only UI;
- tests: recorded by the release checks;
- commit: recorded by the release commit.

## [0.15.0] - 2026-08-31

### Mini App first entry flow

Сделано:

- converted `/start` into an immediate signed Mini App launch;
- registered Telegram `MenuButtonWebApp` as the persistent button beside the
  message field;
- reduced public commands to `/start`;
- attached the same Mini App launch button to durable purchase and result
  notifications;
- retained dormant legacy callback handlers only so old messages fail safely.

Теперь система работает так:

- the bot binds users, grants welcome CAS and delivers notifications;
- all current gameplay starts and continues in the Mini App;
- users always see the main game entry without opening a command list.

Технически:

- migration: no schema change after `0010_independent_daily`;
- tests: recorded by the release checks;
- commit: recorded by the release commit.

## [0.14.0] - 2026-08-31

### Final Telegram player release

Сделано:

- implemented three independent Daily entities and migration
  `0010_independent_daily` without reassigning tickets or completed draws;
- added restart-safe post-settlement transfer of legacy Daily funds into PLL
  with paired immutable ledger records;
- set PSS and KHAN base/current jackpots to 24,000,000 CAS;
- upgraded the one-time welcome target to 100,000,000,000 CAS, crediting only
  the difference for identities that received the earlier grant;
- completed the Telegram Mini App for all lottery codes with a mixed cart and a
  premium blue/red/gold responsive theme;
- removed the ordinary player Web frontend, API, login tooling and Admin
  credential controls while retaining historical schema records;
- added exact-lottery buttons to idempotent result/empty-draw notifications;
- retained Telegram favourites, pagination, next-draw screens and large random
  ticket batches from the final gameplay refinement.

Теперь система работает так:

- Telegram bot and Mini App share the same player, balance, tickets and funds;
- PSS/KHAN run immediately; the purchased shared Daily draw settles normally at
  02:22 MSK and then PLL activates automatically with preserved balances;
- Admin remains a permanent independent HTTPS site.

Технически:

- migration: `0010_independent_daily` (head);
- tests: 134 backend + 8 Mini App + 5 Admin passed;
- checks: Ruff, mypy, frontend typecheck/lint/build passed;
- commit: recorded by the release commit.

## [0.13.1] - 2026-08-15

### Web purchase transaction fix

Fixed the Web-only purchase failure reported after production login and made
current jackpots continuously visible.

Done:

- traced the 500 response to an already-open SQLAlchemy transaction created by
  the authentication dependency;
- assigned Weekly and Daily purchase services a fresh uncached database session;
- preserved the service-owned atomic transaction, row locks, ledger and
  idempotency boundaries;
- added a regression test that verifies both purchase routes cannot reuse the
  authentication session;
- added persistent current-jackpot cards for Weekly and Daily;
- refresh balance/jackpots every 15 seconds, on browser focus and manually;
- translated balance, closed-sales and missing-configuration purchase errors.

System behavior:

- a Telegram-authenticated Web player can buy without a nested-transaction 500;
- the exact application service still performs the entire financial operation;
- a failed purchase does not create a ticket or CAS ledger movement;
- current jackpot values remain visible outside an individual lottery tab and
  update without reloading the whole page.

Technical:

- version: 0.13.1;
- migration: no schema change after `0005_telegram_web_login`;
- backend: 46 typed source files, 131 pytest tests;
- frontend: 8 frozen Mini App + 4 Admin + 5 player Web Vitest tests;
- production deployment requires a new explicit owner command.

## [0.13.0] - 2026-08-15

### One-click Telegram Web login

Removed the unnecessary owner/player credential setup from the normal Web
entry path while preserving password login as a fallback.

Done:

- added **🌐 Открыть Web-версию** to the Telegram main menu;
- added `/web` as a direct command;
- issue a separate one-time link for the currently bound Telegram identity;
- exchange the link for the existing signed HttpOnly Web session;
- allow Web sessions to use the stable player identity without a password row;
- consume tokens transactionally under a database row lock;
- remove the raw token from browser history before the API exchange;
- added expired/reused token handling and a clear retry message;
- retained Admin-created Argon2 Web credentials as an optional fallback;
- updated production configuration and owner/player documentation.

System behavior:

- each Telegram account enters Web under its own K-Loto user in two button taps;
- opening a link from another Telegram account switches the browser session;
- no Web username or password is required for the normal flow;
- a link works once and expires after five minutes;
- balance, active tickets and history are the same in bot and Web.

Technical:

- version: 0.13.0;
- migration: `0005_telegram_web_login`;
- backend: 46 typed source files, 130 pytest tests;
- frontend: 8 frozen Mini App + 4 Admin + 5 player Web Vitest tests;
- Ruff, formatting, mypy and all frontend typecheck/lint/build checks passed;
- Alembic single-head and offline upgrade SQL checks passed;
- production backup completed before migration;
- live migration head: `0005_telegram_web_login`;
- live `alembic check`: no new upgrade operations detected;
- production exchange verified: first login 200, session restore 200, reuse 401;
- Telegram command registration verified: `/start`, `/menu`, `/web`;
- API, bot and gateway restart counts after verification: zero.

## [0.12.0] - 2026-08-15

### Production deployment

Deployed the complete K-Loto backend, scheduler, Telegram bot, player Web and
Admin Panel to the owner-authorized VPS without changing existing VPN services.

Done:

- added a production Docker Compose stack with private PostgreSQL storage;
- built static player Web and Admin clients behind a Caddy HTTPS gateway;
- configured free `sslip.io` hostnames and automatic TLS on port 9443;
- enabled API startup recovery and continuous draw scheduling;
- enabled one persistent Telegram polling bot and notification outbox worker;
- added idempotent Weekly/Daily bootstrap with one future draw per lottery;
- added a compressed database backup script, private backup volume and daily
  cron execution with 14-day retention;
- stored runtime credentials only in ignored/restricted environment files;
- added Admin-based Web credential provisioning for a Telegram-bound player;
- fixed asyncpg compatibility in the initial trigger migrations;
- aligned historical check-constraint names with current metadata.

System behavior:

- backend, scheduler, bot, player Web and Admin restart automatically after a
  process or VPS restart;
- Weekly and both Daily slots are available from the same persistent database;
- the owner can credit a player, configure prices/base jackpots/reserves and
  create a browser login from Admin;
- the player can buy from Telegram or the ordinary browser site;
- HTTPS, database storage and backups no longer depend on the owner's computer;
- the existing VPN continues using its original ports unchanged.

Technical:

- version: 0.12.0;
- migration: `0004_constraint_names` (single live head);
- backend: 45 typed source files, 126 pytest tests;
- frontend: 8 frozen Mini App + 4 Admin + 4 player Web Vitest tests;
- Ruff, formatting, mypy, frontend typecheck/lint/build and secret scan passed;
- live `alembic check`: no new upgrade operations detected;
- live HTTPS/Web/Admin/API/bot/database checks passed;
- API, bot and gateway restart counts after verification: zero;
- an initial non-empty database backup was successfully created.

## [0.11.0] - 2026-08-15

### Daily Lottery 4/15

Implemented the owner-approved Daily economics, scheduling, recovery and player
interfaces without changing Weekly rules or the frozen Mini App frontend.

Done:

- implemented strict Daily 4-of-15 ticket validation and secure RNG support;
- split every purchase into 40% jackpot and 60% distribution ledger credits;
- implemented 0/4 and 1/4 zero payout, 2/4 half-price payout, 3/4 triple-price
  payout and per-ticket sharing of the full jackpot at 4/4;
- used distribution then per-lottery reserve for guaranteed payout shortfall;
- preserved unused distribution and unwon jackpot carryovers;
- reset a won jackpot to the Admin-configured base amount through ledger;
- enabled both 02:22 and 18:00 MSK slots with a two-minute cutoff;
- generalized chronological recovery to Weekly and Daily draws;
- enabled Daily multi-ticket checkout in Telegram and ordinary Web;
- added Daily rules to bot help and all relevant documentation;
- added audited Admin provisioning of player Web credentials;
- recorded OD-006 and OD-012 as resolved.

System behavior:

- Weekly and Daily retain independent draw/ticket numbering and fund accounts;
- identical Daily combinations are separate tickets;
- empty Daily draws complete and carry both pools;
- repeated purchase or settlement invocation cannot debit or pay twice;
- insufficient reserve leaves the whole draw unsettled for safe later retry;
- price, base jackpot and reserve stay owner-controlled in Admin.

Technical:

- version: 0.11.0;
- migration: no schema change after `0003_web_accounts`;
- backend: 45 typed source files, 124 pytest tests;
- frontend: 8 frozen Mini App + 4 Admin + 4 player Web Vitest tests;
- Ruff, formatting, mypy and all frontend typecheck/lint/build checks passed;
- no VPS deployment was included in this release commit.

## [0.10.0] - 2026-08-15

### Player Web

Delivered the simple ordinary-browser player interface requested before Daily,
without changing the frozen Telegram Mini App or duplicating domain logic.

Done:

- added one-to-one `web_accounts` credentials linked to existing regular users;
- added Argon2 password hashing and normalized unique usernames;
- added signed expiring HttpOnly player sessions with CSRF validation;
- added authenticated dashboard, ticket, draw-result and Weekly purchase routes;
- reused `MiniAppQueryService` projections and
  `WeeklyTicketPurchaseService` transaction/ledger guarantees;
- added a minimal responsive React client for balance and Weekly 5 of 20;
- added manual number selection and purchase quantity from 1 to 20;
- added active tickets, settled history and global completed-draw results;
- added a secret-safe interactive Web account configurator and local start script;
- updated architecture, deployment and operator documentation;
- expanded standard checks to all three frontend clients.

System behavior:

- Telegram and Web logins reach the same player, integer CAS balance, tickets
  and immutable results;
- repeated purchase transport delivery remains idempotent and cannot debit the
  balance twice;
- identical combinations remain allowed as separate tickets;
- inactive accounts/users are rejected, and a browser cannot edit balances,
  prices, draws or settlement data;
- production cookies become Secure automatically; local Vite uses a same-origin
  API proxy and does not enable the frozen Mini App development bypass.

Technical:

- version: 0.10.0;
- migration: `0003_web_accounts` (single Alembic head; offline upgrade SQL passed);
- backend: 43 typed source files, 101 pytest tests;
- frontend: 8 frozen Mini App + 4 Admin + 3 player Web Vitest tests;
- all three frontend typecheck, lint and production builds passed;
- implementation secret scan passed; `.env` remains ignored;
- live `alembic check` remains unavailable locally because this machine has no
  PostgreSQL service; migration-chain and offline DDL checks passed;
- no VPS connection or deployment was attempted in this release.

Known:

- Daily payouts and cutoff remain owner decisions OD-006 and OD-012;
- final deployment waits for those rules and the Daily implementation.

## [0.9.0] - 2026-08-15

### Telegram Bot Gameplay

Promoted the aiogram bot from notification adapter to the primary complete
player interface while keeping all business rules in application/domain layers.

Done:

- `/start` now binds identity and opens the live K-Loto gameplay dashboard;
- added balance, Weekly/Daily cards, jackpot, next draw and active-ticket count;
- added Weekly 5/20 inline picker with strict five-number selection;
- added `SystemRandom` random pick, clear, cart and atomic checkout controls;
- identical combinations are preserved as separate tickets;
- the configurable bot cart supports 20 tickets by default;
- each transient cart gets one stable checkout identity for safe callback retries;
- checkout calls the existing locked `WeeklyTicketPurchaseService` and durable
  purchase notification outbox;
- added active tickets, settled history, global results, rules and player
  spend/win/net/match statistics;
- Daily remains visible but blocked until OD-006 and OD-012 are resolved;
- added `/menu` and registered Telegram command descriptions;
- preserved the frozen Mini App compatibility code without using it in the menu;
- documented the final always-on HTTPS Admin/API/bot/Web deployment topology.

System behavior:

- a player can select numbers and buy one or many Weekly tickets entirely in
  Telegram without a domain or Mini App;
- backend remains the source of truth for balance, price, draw and settlement;
- repeated Telegram checkout delivery returns the existing purchase instead of
  charging twice;
- unpaid cart state may be lost on bot restart, but no ticket or CAS exists until
  atomic checkout commits;
- purchased tickets, ledger history, results and notifications remain durable;
- Admin will later be an ordinary persistent website, not an owner-run local
  development process.

Technical:

- version: 0.9.0;
- migration: no schema change after `0002_notification_outbox`;
- backend: 41 typed source files, 95 pytest tests;
- frontend regression: 8 frozen Mini App + 4 Admin Vitest tests;
- Telegram transport batch limit: `BOT_MAX_TICKETS_PER_PURCHASE` (default 20);
- no production/VPS connection or deployment was attempted.

Known:

- the unpaid Telegram picker/cart uses in-memory FSM state for the planned
  single bot replica; shared state is needed only if bot replicas are added;
- Daily purchase remains intentionally unavailable;
- next stage is the simple player Web client, followed by one owner-authorized
  permanent deployment of backend, bot, Web and Admin.

## [0.8.0] - 2026-08-15

### Milestone 6 — Web Admin Panel

Implemented the independent administrative control surface and updated the
product roadmap after the owner froze Telegram Mini App development.

Done:

- added Argon2 login with signed short-lived HttpOnly SameSite sessions;
- added per-session CSRF validation to every administrator mutation;
- added a stable database administrator identity for permanent audit records;
- added system dashboard, players, lotteries/funds and recent activity queries;
- balance and reserve target changes use locked, idempotent ledger transactions
  plus audit records in the same database transaction;
- ticket price and base jackpot configuration requires a reason and creates an
  audit record; Weekly price remains divisible by four for integer payouts;
- added filterable ledger, immutable draw details, ticket/payout archive and
  calculated number statistics;
- created the standalone technical dark-theme React/TypeScript Admin Panel;
- added a credential configurator that writes secrets only to ignored `.env`;
- expanded the standard check script to both frontend applications;
- documented the frozen Mini App and the new Bot → user Web roadmap.

System behavior:

- administrators can trace players, funds, draws and every CAS movement;
- player balance and lottery reserve cannot be overwritten without ledger and
  audit history;
- current jackpot/distribution values remain lifecycle-owned and read-only;
- completed draws remain immutable and expose no write route;
- number intelligence is rebuilt from immutable draw history, not trusted as a
  separate source of truth;
- incomplete administrator credentials disable login safely.

Technical:

- version: 0.8.0;
- migration: no schema change; existing `admin_audit_log` and ledger are used;
- backend: 39 typed source files, 87 pytest tests;
- frontend: 8 Mini App Vitest tests + 4 Admin Vitest tests;
- security: Argon2, HMAC-SHA256 session, HttpOnly/SameSite cookie, Secure in
  production, CSRF token, row locks and idempotency keys;
- browser visual inspection was unavailable because no browser runtime was
  connected; Admin DOM/component tests and production build passed;
- local PostgreSQL integration remains unavailable on this machine; no VPS
  connection was attempted.

Known:

- schedule and payout editing remain locked while Daily cutoff/economics are open;
- production reverse proxy, rate limiting and deployment remain later work;
- Telegram Mini App code is intentionally preserved at v0.7.0 and frozen.

## [0.7.0] - 2026-08-15

### Local Development & Test Mode

Added a playable ordinary-browser workflow before Milestone 6 without weakening
Telegram or production authentication.

Done:

- added a signed local browser session stored in an HttpOnly SameSite cookie;
- restricted session issue/use to development, loopback client, Host and Origin;
- added idempotent `Local Test Player`, Weekly/Daily fixtures and future draws;
- initial user balance, jackpot and reserve are credited through immutable
  ledger entries;
- added a local-only `+ TEST CAS` refill, also recorded through ledger;
- added one-command enable/start scripts and automatic browser launch;
- added an isolated `dev:telegram` frontend mode and Cloudflare Quick Tunnel
  helper that refuses to run while browser bypass is enabled;
- documented PostgreSQL setup and beginner workflows.

System behavior:

- browser testing needs neither Telegram nor a domain;
- the first browser request creates playable local fixtures exactly once;
- restarting does not duplicate the player, lotteries or initial CAS credits;
- Telegram tunnel testing uses real signed `initData`, never the local cookie;
- `APP_ENV=production` makes the development session endpoint unavailable even
  if its enable flag is accidentally set.

Technical:

- migration: no schema change after `0002_notification_outbox`;
- backend: 36 typed source files, 78 pytest tests;
- frontend: 8 Vitest tests, TypeScript, ESLint and production build;
- tunnel: official `cloudflared` Quick Tunnel download/run helper;
- local PostgreSQL integration was not executed because PostgreSQL/Docker is not
  installed on this machine; no VPS connection was attempted.

Known:

- PostgreSQL 16+ remains a one-time local prerequisite;
- temporary tunnel URLs change after restart and must be copied to `MINIAPP_URL`.

## [0.6.0] - 2026-08-15

### Milestone 5 — Telegram Mini App

Implemented the authenticated player Mini App and its backend read/purchase API.

Done:

- created a mobile-first React, TypeScript and Vite application;
- added dashboard balance, Weekly/Daily cards, jackpot and Moscow countdowns;
- added Weekly 5/20 picker, Web Crypto random pick and accessible number states;
- added single purchase, duplicate combinations and atomic multi-ticket cart;
- added active tickets, history, matches, prizes and recent results;
- added Telegram `initData` HMAC/age validation and user binding on every API
  request;
- added a configurable `/start` Web App launch button;
- purchases after 19:55 now prepare and use the next Weekly draw under the
  existing lottery lock.

System behavior:

- price, balance and draw assignment come only from the backend;
- changed, expired, malformed and future-dated Telegram authentication is
  rejected before database access;
- Daily is visible but cannot be purchased until its payout model is resolved;
- cart persistence has no guessed TTL: without owner configuration it stays in
  memory for the current session, while configured storage expires strictly;
- checkout retries use client-generated idempotency keys and the existing
  server ledger protections.

Technical:

- migration: no schema change after `0002_notification_outbox`;
- backend: 34 typed source files, 67 pytest tests;
- frontend: 7 Vitest tests, TypeScript, ESLint and Vite production build;
- dependencies: React 19, TypeScript 5.9, Vite 7;
- local in-app browser visual inspection was unavailable because no browser
  runtime was connected; component tests and production build passed;
- live `alembic check` remains unavailable without local PostgreSQL and no VPS
  connection was attempted.

Known:

- OD-007 exact cart TTL and OD-008 final visual design remain owner decisions;
- Python 3.14 continues to expose pytest-asyncio deprecation warnings.

## [0.5.0] - 2026-08-14

### Milestone 4 — Telegram Bot

Implemented the player Telegram adapter and durable notification delivery.

Done:

- `/start` idempotently binds a Telegram identity and creates a zero-CAS
  balance when needed;
- the bot shows the current balance and directs purchases to the future Mini
  App without exposing ordinary Telegram purchase buttons;
- each committed checkout creates one purchase notification for the complete
  single- or multi-ticket order;
- each committed Weekly settlement creates one result notification per player,
  including all tickets, matches, prizes and zero-win results;
- an outbox worker claims events concurrently, retries failures with backoff and
  recovers stale processing locks;
- unique event keys and terminal sent records prevent routine repeat delivery.

System behavior:

- Telegram outages do not roll back or repeat tickets, ledger entries, payouts
  or completed draws;
- an idempotent business retry cannot create a second notification event;
- notification payload/history is immutable at the PostgreSQL layer;
- only redacted failure codes are persisted.

Technical:

- migration: `0002_notification_outbox`;
- dependency: aiogram 3.x;
- tests cover identity binding, Russian message formatting, multi-ticket
  payloads, result payloads, one-time dispatch and redacted failure handling;
- Ruff and formatting passed;
- strict mypy passed for 31 source files;
- pytest: 58 passed;
- Alembic head and offline PostgreSQL upgrade generation passed;
- live `alembic check` was not run because no local PostgreSQL is installed and
  the project must not connect to the configured VPS during development.

Known:

- Telegram Bot API has no caller idempotency key; a process crash after Telegram
  accepts a message but before `SENT` commits may repeat that message, without
  repeating any business operation;
- pytest-asyncio emits Python 3.14 deprecation warnings in the current toolchain.

## [0.4.0] - 2026-08-14

### Milestone 3 — Scheduler & Recovery

Implemented explicit Moscow schedules, automatic draw preparation and
chronological startup/periodic recovery.

Done:

- Weekly runs Sunday 20:00 MSK and closes sales at 19:55;
- Daily schedule generation uses confirmed 02:22 and 18:00 slots;
- the first draw is the nearest future slot and is never backfilled before the
  system's first start;
- after each Weekly settlement the next numbered draw is prepared;
- startup reconciliation repeatedly settles overdue Weekly draws oldest first;
- APScheduler invokes the same idempotent reconciliation every configured
  interval.

System behavior:

- downtime does not discard a draw or change its official `scheduled_at`;
- `executed_at` records delayed technical execution;
- repeated scheduler processes cannot create a second pending draw because the
  lottery counter row is locked;
- repeated settlement returns the completed result without a second payout;
- Daily payout/settlement remains disabled until its payout model is decided.

Technical:

- migration: no schema change after `0001_domain_model`;
- dependency: APScheduler 3.11;
- tests cover Weekly/Daily boundaries, cutoff, draw numbering, duplicate
  preparation and chronological multi-draw recovery.
- Ruff and formatting passed;
- strict mypy passed for 26 source files;
- pytest: 51 passed;
- Alembic head and offline PostgreSQL upgrade generation passed;
- live `alembic check` was not run because no local PostgreSQL is installed and
  the project must not connect to the configured VPS during development.

## [0.3.0] - 2026-08-14

### Milestone 2 — Weekly Core

Implemented the complete Weekly 5/20 domain mathematics and transactional
application services.

Done:

- canonical ticket validation and atomic multi-ticket purchase;
- duplicate combinations remain valid independent tickets;
- backend chooses the first draw still open for sales;
- one transaction updates balance, ticket numbering, draw totals, jackpot,
  distribution fund and three balancing ledger records;
- official numbers use `secrets.SystemRandom`;
- categories 0/5 through 5/5, reserve fallback and both carryovers;
- completed draw retry returns the existing result without new payouts;
- empty draws receive official numbers and complete normally.

System behavior:

- Weekly prices must be divisible by 4 CAS so 25% prizes are exact integers;
- indivisible equal-split remainders are assigned deterministically by ascending
  public ticket number;
- insufficient reserve aborts the atomic settlement for later retry, without
  using jackpot or creating CAS;
- a won jackpot is fully paid and then receives a ledgered base-jackpot reset.

Technical:

- no schema migration was required after `0001_domain_model`;
- row locks serialize lottery counters, accounts and draw settlement;
- purchase keys are checked both before and after the lottery lock to prevent
  concurrent duplicate checkout;
- Ruff and formatting passed;
- strict mypy passed for 23 source files;
- pytest: 42 passed.

Known:

- PostgreSQL integration tests still require a local Docker/PostgreSQL runtime;
- Python 3.14 causes third-party pytest-asyncio deprecation warnings.

## [0.2.0] - 2026-08-14

### Telegram DevLog integration

Added secret-safe local tools to discover `DEVLOG_CHAT_ID` from an incoming bot
message and send compact development notifications. The helpers load `.env`
without logging values and redact Telegram HTTP/API failures.

Validation:

- Ruff: passed;
- mypy: passed for 5 script modules;
- pytest: 2 passed;
- live test notification: delivered successfully.

### Milestone 1 — Domain Model

Implemented PostgreSQL/SQLAlchemy models for users, configurable lotteries,
draws, immutable tickets, balances, the polymorphic CAS ledger, jackpot
accounts, distribution funds, per-lottery reserves and administrator audit.

Architecture and integrity:

- independent per-lottery draw and global ticket counters;
- unique `(lottery_id, public_number)` constraints;
- integer `BIGINT` storage for all CAS values and balance equations in SQL;
- explicit draw state machine with completed draws as a terminal state;
- PostgreSQL triggers preventing completed draw, settled ticket and ledger
  mutation/deletion;
- idempotency keys and operation IDs for ledger groups;
- row versions on mutable accounts for concurrency diagnostics;
- Weekly and Daily represented as separate configurable lottery entities.

Migration:

- `0001_domain_model` creates all tables, indexes, foreign keys, checks and
  immutability triggers;
- offline PostgreSQL SQL generation passed.

Tests:

- Ruff and formatting passed;
- strict mypy passed for 21 source files;
- pytest: 11 passed.

Resolved:

- reserves are scoped per lottery, following the Milestone 1 requirement.

Known:

- schema migration was compiled offline because local Docker/PostgreSQL is not
  installed; it was not executed against the configured VPS.
- pytest-asyncio emits Python 3.14 deprecation warnings in the current toolchain.

## [0.1.0] - 2026-08-14

### Milestone 0 — Foundation

Established the project foundation as a modular monolith with replaceable bot,
Mini App and Admin clients.

Added:

- repository structure and long-lived agent rules;
- FastAPI application and database-aware health endpoint;
- typed environment configuration with secret placeholders;
- asynchronous SQLAlchemy session infrastructure;
- Alembic migration framework;
- pytest, Ruff and mypy configuration with foundation tests;
- PostgreSQL/API Docker Compose skeleton;
- architecture and open-decisions documentation.

Architecture decisions:

- one backend and one database preserve simple, explicit transaction boundaries;
- domain/application layers remain independent from Telegram and React;
- UTC persistence and explicit Europe/Moscow schedule rules;
- integer CAS and an immutable ledger for every future balance movement.

Risks found:

- reserve scope, integer split remainders and insufficient-reserve behavior need
  owner decisions;
- Daily second draw time, payout model, prices and cart TTL remain unresolved;
- notification delivery must later use an after-commit retry/outbox boundary.

Validation:

- Ruff lint: passed;
- Ruff format check: passed (31 Python files);
- mypy strict check: passed (16 source files);
- pytest: 4 passed;
- Alembic offline SQL generation: passed;
- Docker Compose runtime validation: not run because Docker is not installed in
  the current environment.

Known limitations:

- no domain tables or gameplay logic are included before Milestone 1;
- frontend and bot directories are architectural boundaries only;
- production deployment was intentionally not attempted.


## 2026-09-05 — Kasper Bingo 1.20.0

- Owner confirmed daily 22:00 Moscow, 58/60 draw, 28 inclusive jackpot cutoff,
  50 tickets/player/draw, 50,000 CAS price, 100,000/500,000 CAS shared tour pools,
  and 10bn base jackpot. See OD-019; the earlier weekly concept is superseded.
- Added 2,000 preprinted tickets/draw, immutable row order and atomic inventory
  claims using the existing purchase ledger. Migration 0033 pairs initial jackpot
  funding with a Kasper Fund debit; purchased/completed history is untouched.
- Bingo persists its random sequence at broadcast start, only publishes a prefix,
  and settles after 58 two-second reveals. Recovery reuses the stored sequence.
  Jackpot at broadcast start is frozen; later sales remain in the next jackpot.
- Added a dedicated responsive Bingo page, real DOM paper tickets, selection,
  serial numbers, detailed tickets, individual live switching and a manual best
  ticket action. No barcode, raster mockup, external font or mass ticket rendering.
- Focused PostgreSQL smoke runs against a disposable restored database only:
  pool uniqueness, concurrent claim, retry, 50-ticket limit, hidden sequence,
  settlement retry and ledger conservation passed. It caught and resolved an
  inventory FK flush-order issue before production.
- Browser QA unavailable: CUA returned no browsers. Automatic approval review
  rejected headless Chrome screenshot launch with "blocked by policy". No visual
  browser verification is claimed.
- Release validation: Ruff, formatting, mypy, backend suite (181 tests plus the
  added missed-draw case), Mini App lint/typecheck/build and 51 tests passed.
  Admin typecheck/lint/build and all 18 tests passed (251 tests total).
  The focused PostgreSQL smoke also verifies that next-draw purchases made during
  a broadcast survive the current jackpot payout.
- Deployed API + gateway after a production backup. Alembic schema/backup checks
  passed, API/DB healthy. Public Mini App and Admin HTTPS/health return 200, CSS/JS
  match local artifacts, Mini App manifest 1.20.0, Admin anonymous dashboard 401.
- Production read-only verification: first Bingo draw 2026-09-05 22:00 Moscow,
  cutoff 21:58; inventory 2,000 tickets; owner auto-play bought five tickets;
  jackpot 10,000,250,000 CAS; base 10bn; paired startup ledger sums to zero;
  scheduler has no error. Admin remains 1.19.0; existing bot process preserved.
## [1.42.6] - 2026-09-23

- Polished Mini App navigation and balance capsule responsiveness.
- Fixed PULSE live status text to format secondary values with the draw's server-provided offset.
## [1.42.7] - 2026-09-23

- Started the web visual foundation: fixed club navigation on desktop, responsive navigation on smaller screens, live status treatment and layered scene styling.
## [1.42.8] - 2026-09-23

- Hardened GROБ routing for production data where the display name and internal lottery code can differ.
## [1.42.9] - 2026-09-23

- Added the existing GROБ coffin artwork as the visual backdrop for the web picker and increased scene contrast.
- Added a lazy-loaded Phaser canvas layer isolated to GROБ; React remains responsible for controls and server-backed state.
## [1.43.0] - 2026-09-23

- Reworked GROБ visual composition after production review: one real coffin scene, no overlapping canvas/wireframe treatment.

## 2026-09-23 — «ГРОБ» 2.5D polish and global live-tab routing

- Removed the in-experience live switch. The Grob broadcast now mounts only in
  the shared web «Эфир» tab; that tab polls both the ordinary standard feed and
  the existing Grob-filtered feed so an active Grob window is not hidden by a
  different standard draw.
- Added a central illuminated purchase-seal control and result-stele asset, curved
  number-seal travel, channel illumination, layered mist/parallax, purchase sealing/cassette
  motion and distinct quick-purchase feedback without changing purchase/API rules.
- Rebuilt the live composition around three stone stelae, server-timed reveal,
  highlighted player seals and a server-authored result ribbon. Late join renders
  already revealed numbers immediately and animates only a newly reached marker.
- Used a temporary local review entry with simulated presentation state for owner
  acceptance, then removed it before release.
- Focused validation: TypeScript and ESLint passed; Vitest 27/27 passed; Vite
  production build passed. Desktop and 390×844 browser QA covered manual purchase,
  automatic empty-ticket reset, x5/x25 feedback, live reveal/result and a clean
  console after fixing the reveal camera tween. No deploy was attempted pending
  explicit owner visual approval.
# 2026-09-24

- Проверена production-нумерация Casper Dual: `next_ticket_number=3992`, 3 991 купленный билет, диапазон публичных номеров 1–3991. Нумерация началась с 1 и корректно растёт в пределах этой лотереи; историю билетов не изменяли.
- Исправлена нижняя сводка выбранных чисел: общий CSS для 32×32 значков `<i>` ограничивал ячейки NIGHT/DAWN, числа вываливались вниз. Заменены на отдельные адаптивные текстовые ячейки. Локальное дизайн-превью проверено с NIGHT 3·10 и DAWN 4·6 на ширинах 520/390/320 px.

- Пересобран первый экран Casper Dual в Mini App: вертикальный hero заменён на компактную шапку; изображение исходного разрешения размещено по ширине всей страницы без увеличения и кропа, карточки поверх него полупрозрачны. Добавлены полный джекпот, число билетов, отсчёт и номер ближайшего тиража. Билет и два циферблата видны сразу на телефонном экране.
- Выбор чисел разделён на неподвижный `dual-number-slot` и внутренний шарик: короткий pop при выборе и цветное свечение не влияют на координаты. Уменьшены диаметр шарика и наложение соседей. Проверено дизайн-превью на ширине 390 и 320 px с выбранными соседними числами 11/12; Mini App lint/typecheck, 74 теста и build пройдены.

- Исправлен выбор чисел Casper Dual: Framer Motion перезаписывал CSS-смещение кнопок при нажатии, из-за чего цифры вылезали за пределы циферблата. Кнопки сделаны статичными, радиус расположения уменьшен, выделение переключено на цвет/свечение; существующий Telegram haptic сохранён. Тест проверяет запрет третьего числа в каждом поле. Mini App: typecheck, lint, 74 теста и build прошли; локальное дизайн-превью проверено с выбранными 5/6 в NIGHT/DAWN на узком экране.

- Casper Dual реализована как новая ежедневная лотерея: миграция создаёт продукт и два поля результата для одного билета; покупка привязывает его к двум следующим тиражам; расчёт фиксирует промежуточный результат, оставляет билет активным и платит только после второго.
- Деньги проходят через ledger и Kasper Fund; стартовый фиксированный джекпот 5 млн CAS выделен в отдельный счёт. NIGHT/DAWN — терминология игрока, backend использует draw. Веб-канал исключает Dual до отдельного запуска.
- Mini App использует предоставленную сцену в WebP (около 303 КБ), фирменный логотип, два тактильных циферблата, карточку каталога, ×1/×5/×25 и отдельный билет с фазами. Избранные числа не показаны.
- Проверки: новые backend-тесты покрытия фаз, цены и выплат; Mini App lint/typecheck/build и браузерная визуальная проверка. Полный набор backend-тестов пройден вне sandbox для доступа к временным файлам.

# 2026-09-25 — Docker storage maintenance

- Production disk audit found 9.855 GB of unused build cache and 7.595 GB of nominally reclaimable images; 64 database dumps occupied 1.30 GiB and system journals about 1 GiB.
- Pruned only unused build cache above a 2 GB reserve and unused images older than 48 hours; free disk space rose from 18 GB to 26 GB. Running containers, volumes, and backups were preserved.
- Added post-health release housekeeping to cap build cache and remove only old, unused K-Loto-labelled images, leaving recent release images available for rollback.

## Casper LIVE casino scratch experience — 2026-10-05

- Replaced the generic hero/spinner with burgundy lacquer, gold foil, tactile ticket frames, embossed symbol artwork and a generated 3D medallion using the approved Casper C-and-ball logo reference. The imagegen skill guided the brand-referenced asset; transparent output is encoded as a 378 KB WebP in Mini App public/assets.
- One/three selection uses one explicit purchase CTA. Server settlement updates the parent balance immediately; no decorative wait. All purchased tickets appear together, with pointer scratching, tap/keyboard reveal and a fixed open-all action. Prize styling and aggregate results wait for reveal; authoritative results remain server-provided. History stays readable after reopening.
- Guarded duplicate clicks and stale initial history responses. Reduced-motion disables decorative animation; responsive checks use synthetic design-preview purchases, never production transactions. Gateway-only publication preserves Web/Admin assets under the shared VPS operations lock with source/database backups and HTTPS health verification.
- Verification: Mini App typecheck/lint/production build passed, all 114 Mini App tests passed and the three focused purchase/reveal/error regressions passed after final presentation edits. Browser smoke at 390×844 and 320×640 verified single/triple reveals, real multi-stroke canvas erasure, reachable fixed actions, full brand-image loading, no horizontal overflow and no console errors. Backend: 303 passed, one existing Windows symlink skip; whole-project Ruff has eight pre-existing errors, format check seven pre-existing files, and mypy three pre-existing errors in application/dual.py. No backend source changes.
- Published 1.56.0 (d114568): local release/production rollback archives and PostgreSQL backup retained; shared operations lock covered backup/upload/build/restart/health. Gateway configuration validated, public HTTPS returned exact release HTML/version, exact brand WebP and health 200. Web/Admin file fingerprints and API/bot/database container identities are unchanged. Mobile review screenshot: .tools/casper-live-156-home.jpg. No real ticket purchases were made during verification.

## Casper LIVE brand labels — 2026-10-05

- Owner clarified that the product never uses casino terminology. Hero now reads CASPER LIVE and «Мгновенная лотерея», without fictional edition numbering. Approved medallion artwork, layout, scratching, prices and result mapping are preserved. Scope: two visible labels and PATCH version 1.56.1; Mini App typecheck/lint/build and focused mobile smoke, followed by locked gateway-only publication and health verification.
- Published 1.56.1 (7a50959): typecheck/lint/build and label/image browser smoke passed. Local and VPS rollback archives plus database backup retained; public HTTPS serves exact HTML/version/brand artwork and health 200. Web/Admin fingerprints and API/bot/database identities are unchanged.

## Casper LIVE prize symbol hierarchy — 2026-10-05

- Shared native SVG symbol renderer replaces generic signs in scratch tickets and account history: existing server IDs 2–7 now depict bronze clover (1,000 CAS), silver coin (2,000), gold star (5,000), ruby (20,000), diamond (100,000) and approved Casper C-and-ball gold medallion (1,000,000). Loss ID 1 uses a horseshoe; legacy ID 8 remains a seven. Distinct materials/facets/relief are presentation only; stored combinations, prizes, ledger and odds remain untouched.
- Added a collapsed symbol/prize reference. It describes the existing fixed server categories and is never consulted by purchase/settlement logic. One shared component keeps historical and new ticket presentation consistent. Publication scope: Mini App/gateway only under the operations lock, preserving other frontend assets.
- Verification: Mini App typecheck/lint/build passed; all 114 existing tests passed plus the four focused reveal/settlement/error/max-prize tests, including the new branded maximum-prize regression. Synthetic browser smoke at 390×844 and 320×640 verified the six prize rows/materials, three-ticket fast reveal, recorded ruby/star history, no horizontal overflow and no console errors. Review screenshot: .tools/casper-live-157-symbols.jpg. No backend changes or real purchases.
- Published 1.57.0 (676aee8): source/assets/database backups retained, shared VPS lock held across backup/upload/build/restart/health, gateway validated and public HTTPS confirmed exact HTML/version/brand asset plus health 200. Web/Admin fingerprints and API/bot/database container identities unchanged. Two transient SSH failures happened before any remote mutations; third connection completed publication.
## Publication emergency stop — 2026-10-06

- Owner stopped channel automation after routine Fast draw results were incorrectly included in the historical replay. Persistently disabled `publication.transport` under the shared event lock on production. Stop confirmation: 100 sent, 17,191 queued, no sending or uncertain rows. Remaining queue is blocked; no published messages or event history were deleted. Do not resume without owner authorization after correcting event eligibility.

## Fast publication eligibility correction — 2026-10-06

- Added a shared configured exclusion for routine per-draw Fast results, combinations, jackpot carryovers and ordinary winning-ticket notices. Both collection/snapshot and final outbox selection enforce eligibility independently of historical draft approval, including existing queued rows. Significant threshold/record/jackpot events and ordinary-lottery results remain available.
- Explicit owner-authorized restart requeues all eligible events since 25 September, even previously sent ones, preserving prior delivery receipts. Excluded rows remain in the audit with blocked delivery and no approved Story visibility. No draw/ticket/ledger history changes, no schema changes. Scoped regression tests and backend static checks; owner explicitly skips new backups and broad release checks.

## Strict publication criteria and retired participant records — 2026-10-06

- Stopped delivery again after owner identified ordinary non-Fast results and repeated small weekly “records”. The initial Fast-only fix was insufficient: design subcategories and permission to deliver drafts had been mistaken for qualified events.
- Replaced broad automatic eligibility with an explicit configured event allowlist at generation, approval and outbox delivery. No routine draw result/combination/carryover/winner-count posts for any lottery, and no repeated A5 snapshots. Retired A4.3/A5.2 across catalog, feeds and approval, preserving snapshots/assets and audit history.
- A5.5 now compares distinct paid winning users for a single draw with previous same-format draws and requires a NEW maximum strictly above 20. Ordinary ticket and platform counters retain separate meanings. “3 сентября” verified active; it is a lottery name, not an out-of-window event date. Focused tests: 95 passed; scoped Ruff/mypy and production health for API-only correction, with no new owner-disallowed backups.

## Corrected replay completed — 2026-10-06 04:50 MSK

- Production API 1.50.2: all 264 eligible historical posts delivered, first new message ID 184; no eligible pending/in-flight/uncertain replay rows. Final compact status: transport enabled, invalid queued events 0, Stories 10, ongoing automatic interval 1,800 seconds. “3 сентября” remains active. Unique-participant scenarios are retired; unique-winner records require a new per-draw maximum strictly above 20.
- Existing retention cleanup passed production health, removed six obsolete gateway images and reclaimed about 396 MB; the three redundant local publication source archives were removed. No new database/source backups were created for this correction at the owner's request. Previously mistaken channel messages (161 receipts now outside the allowed scenarios) remain; publication audit and completed financial/draw history were preserved.


## Publication editorial cleanup — 2026-10-06

- API 1.50.3: removed service footer and automatic artwork date; non-jackpot B statistical copy uses plain periods without dates. Removed 198 original Fast template rows, retaining six owner scenes (192 raw template choices); the asset compiler now replaces original Fast layouts. Existing queued snapshots are normalized before rendering. Published messages are not retroactively edited.
- Configured jackpot record gap 100,000,000 CAS for A1.3/A1.4/B2.1, applied at generation and SQL delivery boundary. Factual maxima remain separate from announced/queued editorial checkpoints so minor changes accumulate. No schema, ledger, ticket or draw changes; no historical replay. Focused publication regressions and Ruff/mypy before API-only release; health verified after deployment.

## Telegram Stories player — 2026-10-06

- The native dialog top layer bypassed the app-shell safe padding, placing story controls under Telegram controls. Added dialog-specific safe top/bottom/side geometry with a fullscreen fallback, responsive complete artwork sizing, compact progress/header and accessible tap targets.
- Added left/right tap and swipe navigation, downward close, seven-second playback, remaining-time-preserving pause and hold-to-pause, background-tab pause, keyboard navigation and final-item close. Body scrolling is locked only while viewing; the existing lottery CTA remains above tap zones.
- Mini App 1.59.2: eight focused Stories tests plus affected lint/typecheck/build. Browser smoke at 390×844 and 320×568 verifies dialog top 80px with simulated Telegram insets, artwork inside bottom safe area, real tap navigation and uncovered CTA; screenshots inspected. Gateway-only deploy preserves automatic publication transport and API.

## Telegram post Mini App link — 2026-10-06

- Owner requested a Mini App link at the end of channel posts. Shared HTML caption formatting appends the clickable label to new automatic and manual sends, including previously prepared queue rows; existing matching links remain single. Snapshot validation reserves the visible footer inside Telegram’s UTF-16 photo caption limit. Existing published messages remain unchanged; no replay or business-history changes.
- API 1.50.4: focused caption/publication tests and scoped static checks; API-only deployment under the operations lock with backups, diagnostic archival and health verification.


## Ready publication proposals — 2026-10-08

- API 1.50.5 / Admin 1.56.1: default ready-proposal cards, separate history/manual editor, server-side approval filtering before pagination. Owner keeps automatic A/B transport unchanged; calculated drafts require explicit acceptance.
- On admin load/refresh, existing B3 adapters prepare current statistical drafts using stable daily keys, without a recurring summary job or automatic approval. Event copy/layout can be edited while preserving source payload, event identity and calculated value/fact; queued/sending events remain protected.
- Draft deletion cancels delivery and hides the snapshot from all admin/player feeds, retaining an audited tombstone/key so refresh cannot resurrect it. Shared event lock and revision checks serialize editorial changes with collection/delivery. No Telegram posts are sent or removed by release checks; no schema, ledger or draw changes.
- Focused publication backend regressions, four editor UI tests, affected lint/typecheck/build and production health/ready-draft smoke; deployment only API and gateway under the operations lock with standard backup/diagnostic preservation.


## 2026-10-09 — Casper Vault implementation

- Added approved Vault domain rules, separate authenticated purchase/history endpoints, admin summary and game-aware ticket history. Reused atomic Fund/balance locking and immutable ledger settlement; no schema transition or refunds.
- Added generated golden treasury artwork, separate readable hero copy and a tactile wheel with five unlocking bolts, retained progress, viewport lock, keyboard alternatives, reduced motion and reveal-all. Added catalog and account integration.
- Full backend suite: 455 passed, one Windows symlink capability skip; mypy: 73 files clean. Exact 10,000-roll distribution, expected payout, replay/owner/quantity isolation and insufficient coverage regressions included. Root Ruff has pre-existing findings; affected files are checked separately. Frontend and isolated PostgreSQL/publication checks follow below.
- Mini App lint/typecheck/build clean. Suite covered 143 tests: four initial failures (three lazy-load timeouts under concurrent host load and one wheel rounding regression) were resolved by a focused 43-test run after fixing the rounding boundary; the other 100 passed in the initial suite. Admin lint/typecheck/build clean, all 39 tests pass with limited worker concurrency, including Vault summary navigation.
- Built browser smoke at 320/390/430 px: no horizontal overflow, hero text stays above artwork. Pointer wheel retains three unlocked bolts after release, fixes the viewport only while dragging, opens a ticket after 540 degrees; reveal-all opens the other two. Purchases in the isolated design fixture only; PostgreSQL clone checks cover real settlement before publication.
- Published API 1.54.0 / Mini App 1.64.0 / Admin 1.58.0 under the VPS operations lock with production database, source/assets and previous service-image backups. Preserved API/bot diagnostics before recreation. Disposable PostgreSQL backup clone passed rollback, concurrent idempotency, three-game key/history isolation, ledger settlement and historical row-hash preservation; only the clone was removed.
- Production health HTTP 200, Alembic reports no schema changes; API/bot/gateway running and database container identity retained. Web fingerprint unchanged. Exact published Mini/Admin/Web HTML and Vault artwork match built files. Public catalog shows LIVE/Aurora/Vault, 5,000 CAS ticket, 5m maximum; at 320/390/430 px copy remains above artwork without horizontal overflow. Read-only production audit verifies API version, complete Vault distribution, routes and Fund coverage; Vault history/Admin endpoints return 401 without authentication.
- Auto-review rejected an additional purchase smoke in the production preview because it could debit real funds; no purchase was executed or retried there. Purchase mechanics remain verified by the local fixture and monetary checks by the isolated PostgreSQL clone. Public production checks stayed read-only.


## 2026-10-09 — Instant header and repeat-purchase regression fix

- Standalone Aurora/Vault roots now use app-safe insets (Telegram device and content-safe areas plus browser environment) with rules after responsive CSS overrides, matching LIVE's established safe-top behavior.
- All three repeat buttons invoke the existing authenticated purchase API directly, retain one/three quantity, display cost, guard low balance and double clicks, and replace the previous result only after success. Errors remain visible on the result screen. LIVE gains the same stable request-key retry behavior already used by Aurora/Vault; authoritative server settlement is unchanged.
- Added shared regression coverage for one/three direct repeat, fresh keys after success, busy duplicate prevention, retained result on uncertain failure, stable retry key and updated insufficient balance for all three games. Frontend-only patch: scoped tests/lint/typecheck/build and built safe-area smoke; gateway publication follows.
- Validation: Mini App lint/typecheck/build clean; 21 affected tests passed. Built browser smoke confirmed safe-top 103 px (59 device + 44 Telegram controls) at 320/390/768 px, without horizontal overflow; repeat buys new sealed single Aurora ticket / three Vault tickets directly, with no quantity menu. Purchases were local preview fixtures only.
- Published Mini App 1.64.1 under the operations lock after database/source/assets/image backups; restarted gateway only. Exact public HTML, affected instant JS/CSS and version verified; health HTTP 200. API/bot/database container identities and Admin/Web fingerprints unchanged. Read-only public browser smoke confirms Aurora/Vault use 103 px padding when Telegram safe-area variables are supplied. No production test purchases.

## 2026-10-09 — Distribution draws implementation

- API 1.55.0 / Mini App 1.65.0 / Admin 1.59.0. OD-050 resolved; owner explicitly excludes Dual entirely. Scheduled games including Fast only, existing purchased tickets remain eligible until exact sales cutoff; completed draws immutable. Immediate text-only announcement, no story/image or generic publication automation activation.
- Add migration 0050: draw designation/result fields, nonnegative distributed CAS and unique durable announcement per draw. Assignment locks draw, checks cutoff after acquiring lock, audits once; replay creates no extra announcement or money entries. Calendar projects future official slots without writes; confirmation prepares chronological intermediate draws under lottery lock and handles concurrent scheduler creation.
- Domain roll-down retains ordinary payouts, walks exact tier order (Bingo tour 2/1), falls back to all paid tickets, distributes integer CAS deterministically, restores snapshot base from Fund. Settlement uses existing transactional locks/ledger and suppresses false jackpot-win events for distribution recipients. Empty draws carry the jackpot.
- Dedicated announcement delivery bypasses the generic publication gap, commits receipt claim before Telegram I/O, retries definite throttling only, marks uncertain transport/crashed senders without blind duplicate, and expires stale queued posts. Admin previews text, confirms in a separate step and shows delivery state; player headers/live/Fast show only the current draw flag.
- Validation: backend 484 passed / 1 Windows symlink skip (Linux check follows during release); mypy 75 files; scoped Ruff; Admin 42 and Mini App 153 tests passed; affected lint/typecheck/build. Local mocked Admin confirms Dual/instant exclusion, 145 existing tickets, preview-before-send and published status. At mobile widths the shared nav scrolls internally; the new form fits. Disposable PostgreSQL clone accounting/concurrency/rollback/history and exact public asset checks are required before activation. No real distribution assignment or channel message is made for testing.
- Publication completed: commits 04f5d64 / 461d161 deployed under the full VPS operations lock after database/source/image backups. Disposable PostgreSQL clone passed concurrent assignment/settlement, injected rollback, full jackpot + ordinary payouts, ledger zero sum, unchanged purchased history/completed draws and mocked exactly-once text delivery. Additive migration 0050 applied before writers restart; production Alembic check has no pending operations, API healthy, bot/gateway running. HTTPS health 200 and exact Mini App 1.65.0/Admin entry HTML+JS/CSS verified; Web fingerprint and database container unchanged. No production designation, test purchase or Telegram channel post was created. The single host-dependent Windows symlink test remains unavailable locally; clone runs on Linux and exercises real PostgreSQL financial transactions.
- Publication completed: commits 04f5d64 / 461d161 deployed under the full VPS operations lock after database/source/image backups. Disposable PostgreSQL clone passed concurrent assignment/settlement, injected rollback, full jackpot + ordinary payouts, ledger zero sum, unchanged purchased history/completed draws and mocked exactly-once text delivery. Additive migration 0050 applied before writers restart; production Alembic check has no pending operations, API healthy, bot/gateway running. HTTPS health 200 and exact Mini App 1.65.0/Admin entry HTML+JS/CSS verified; Web fingerprint and database container unchanged. No production designation, test purchase or Telegram channel post was created. The single host-dependent Windows symlink test remains unavailable locally; clone runs on Linux and exercises real PostgreSQL financial transactions.

## 2026-10-11 — Distribution results and 24-hour editorial proposals

- API 1.55.1 / Admin 1.59.1; OD-051 resolved. Read-only production audit identified paid PULSE distribution #5649 (168,341,840 CAS), which had reset the fund but not the event-based drought counters. Shared cycle queries now recognize positive `distributed_amount` as a reset alongside genuine wins and use scheduled chronology. Completed history, CAS rules and ledger remain unchanged.
- Migration 0051 preserves schedule receipts and permits a unique schedule/result pair per draw. Successful distribution settlement queues the text recap atomically with money/result state, including full-combination wins and empty carry-forward draws. Delivery works after scheduled time, survives definite outages, and retains uncertainty instead of blind duplicates. Upgrade recovery is limited to fresh missing receipts, so the old October 9 draw is not retrospectively posted.
- Proposal retention applies to unanswered drafts, with creation/source-event age capped at 24 hours; filters precede pagination and automated archival keeps audit/tombstones. Old series proposals are suppressed after resets, including queued obsolete series claims. Published/archived history and unrelated authorized deliveries retain their state. Admin hides expired proposals on an open page, refreshes suggestions every minute and protects unsaved editor text.
- Regression checks cover paid/empty/won resets, statistics epochs, integer payout summaries, receipt creation, delayed result delivery, exact expiry, old imported events, immutable history and editor refresh. Extended disposable PostgreSQL smoke verifies atomic result rollback, concurrent settlement, unique receipts, real SQL freshness/epoch filters and audited idempotent archival before production activation.
- Local validation: backend full suite 505 passed / 1 Windows symlink skip; mypy 77 source files and scoped Ruff clean. Admin lint/typecheck/build and all 45 tests passed, including focused open-tab expiry/refresh/editor smoke. Shared optional event typing also passes Mini App/Web typecheck; their assets remain at existing versions and are not rebuilt. PostgreSQL migration/transaction checks and production verification follow under the release lock.
- Published commits 6607e60 / cb2c659 under the complete VPS operations lock, with database/source/assets/image backups and API/bot diagnostic archives before recreation. Disposable PostgreSQL clone passed migration 0051/Alembic drift check, concurrent assignment and settlement, financial/result-outbox rollback, zero-sum ledger, unchanged purchased/completed history, schedule/result uniqueness and mocked delivery, plus SQL freshness/epoch filtering, rejected expired publication and audited idempotent archival. Clone removed by exact database name.
- API/bot/gateway updated; production health HTTP 200 and Alembic check clean. Exact Admin entry HTML/JS/CSS verified over HTTPS; Mini App 1.65.0 and Web assets/fingerprints, database container identity unchanged. Read-only production audit confirms API 1.55.1/schema 0051, three fresh suggestions, zero pending obsolete series claims, and PULSE drought 200 matching exactly the 200 completed draws after paid distribution #5649. Its 168,341,840 CAS distribution, payout and 2,555,555 closing jackpot are unchanged; its old result was not retrospectively posted. Linux container runs the locally unavailable symlink regression successfully on temporary fixtures. No production test purchase, designation or test channel message.


## 2026-10-11 — Storage audit and retention coverage

Read-only production inspection found 89% filesystem usage and a second source
backup directory outside existing maintenance coverage. Extended only known
archive/upload filename families, recognized feature rollback tags, and restored
seven-day cleanup eligibility for project-labelled legacy gateway images.
Retention windows, business data, volumes and database backups are unchanged.
Full backend suite: 512 passed, one Windows symlink skip; the Linux-only check
will run on production with disposable filesystem fixtures before cleanup.


## 2026-10-11 — Mini App read paths and repeated purchase latency

Baseline production read-only measurements: 31 dashboard queries, 3.0–4.4 s for
an account with 118k tickets; unused recent history consumed 2.2–3.0 s. Full
account statistics cost about 1 s. Replaced per-lottery queries with batched draws
and ticket counts, omitted unused history from dashboard HTTP responses, cached
only public display totals for 15 s, indexed user/draw/status and open draws via
concurrent-index migration 0052. History grouping now uses indexed group counts.
Normal initialized Telegram identities read the existing grant receipt without
balance locks or upserts. Legacy/new identities retain transactional setup.

Mini App prioritizes dashboard, removes the 480 ms post-confirmation wait and
full profile refresh on each scheduled purchase. In-flight guards block double
submits; request generations reject older account/dashboard responses after a
purchase. Scheduled idempotency receipts now verify account ownership.

Validation: full backend 512 passed / one Windows symlink skip; mypy 78 modules;
Mini App 155 tests. Linux maintenance fixtures passed including symlink safety.
Release includes isolated PostgreSQL backup-clone checks for concurrent identity
initialization, repeated 25-ticket purchases, duplicate replay, receipt ownership,
ledger reconciliation and preservation of existing tickets/completed draws.


Repository-wide Ruff check now passes. The only seven outstanding findings were
long lines in migration 0045; formatting preserves its exact original Python AST
including every SQL string. No historical migration logic changed. All three
clients pass lint/typecheck/build; Admin 45 and Web 35 tests pass. Mini App totals
156 tests after the additional lottery-opening/purchase-response race regression.


Storage sweep completed with health passed: 847,052,800 bytes reclaimed, around
5.0 GiB free before the next release backup. Raised maintenance unit timeout from
10 to 30 minutes because the first ownership-revalidated image sweep took more
than ten minutes; no retention window or deletion scope is relaxed. Production
read-only integrity audit found zero balance/ledger mismatches, zero scheduled
draws overdue by ten minutes, and zero invalid indexes. Existing purchase throttle
is ten requests per five seconds; its safety setting remains unchanged.


## 2026-10-11 — Performance release production verification

Published API 1.55.2 / Mini App 1.65.1 under the operations lock, with database,
source/assets and image rollback backups and preserved API/bot diagnostics.
PostgreSQL backup-clone smoke passed: 25-ticket purchase plus identity 39.7–111.3
ms; concurrent replay created one purchase; 225 tickets total; balanced ledger;
original ticket/completed-draw hashes unchanged. Clone dropped. Migration 0052
and Alembic check passed; database container retained. HTTPS health 200 and exact
served entry files verified. Web asset fingerprint unchanged.

Production read-only measurements: large-user dashboard first 1197 ms then
41/16 ms (31 SQL previously, 9 first/5 warm now); second account 126/87/62 ms.
Account aggregates remain costly (0.66–6.53 s during post-build measurements),
recorded as follow-up in docs/TECHNICAL_AUDIT_2026-10-11.md. Before/after integrity
checks found zero balance-ledger discrepancies, overdue draws >10m or invalid
indexes. Disk after backup/build: 92%, 3.2 GiB free; increase capacity is priority.
Parallel unrelated Caddy/Dockerfile/legal-miniapp changes were left untouched.
## [Approved achievement rewards and automatic gifts — local only] - 2026-10-20

Owner approved the complete 22-row table: 930,000 CAS, eight daily-draw gift
tickets and four planned cases; requires a neat gift marker and no case system.
Recorded OD-069. CAS now transfers from Kasper Fund with a balanced two-row ledger
operation per reward part. Automatic tickets reuse the authoritative purchase and
settlement services, zero user cost, GIFT provenance/unique reward FK, usual funded
jackpot/burn allocation and frozen nominal price for payouts. Paid-only conditions
exclude gifts, while real prize payments still update the balance.

Migration 0061 preserves immutable history and adds bounded indexed deferred
delivery. Each payable part commits separately to avoid fund/lottery lock inversion;
unavailable draws/funding wait five minutes without blocking player events. Cases
stay planned catalog/award metadata, outside retry scans, with no inventory or
delivery. Existing unpriced awards remain frozen; a new local preview profile
exercises approved rewards while retaining the prior profile and both DB backups.

Gift icon and label appear on ticket rows/full tickets. Mixed rewards appear in
cards/details/notices, future cases are explicit, and finite event-driven refresh
updates balances/progress. Local launcher tolerates offline draw recovery with a
visible progress message. No production connection or publication in this task.

Validation: backend 807 passed / 1 Windows symlink skip; Mini App 194 passed;
Admin 68 passed; both client lint/typecheck/builds, Ruff, mypy 102 files, Alembic
schema check. Real PostgreSQL coverage includes conservation, odd-price burning,
duplicates/concurrency, unavailable funds/draws, recovery and gift settlement.
Live local browser smoke produced six achievements and one gift through three
paid purchases. 320/390 px visual QA passed. Full report:
docs/achievements/ACHIEVEMENT_REWARDS_LOCAL_REPORT.md.

Candidate gate caught an empty-database initialization regression before promotion: economy_control may have no row during bootstrap. Both lottery migrations now coalesce the missing epoch to the schema default 1; an existing production epoch remains unchanged. Fresh local bootstrap through 0067 and alembic check pass. Restore verification computes deterministic bucketed row hashes on PostgreSQL, comparing every old financial row without repeatedly transferring the full archive into Python. First failed attempt preserved at archive/local/2026-10-22/lotteries-release; corrected attempt has a separate archive.
