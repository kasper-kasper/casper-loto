# Web Admin Panel

Milestone 6 provides a separate React/TypeScript interface at
<http://127.0.0.1:5174>. It is not embedded in Telegram and contains no lottery
or CAS business logic.

The local `5174` workflow is development-only. In the final deployment the
compiled Admin client will be served continuously by the HTTPS reverse proxy;
the owner will open its normal URL and log in without starting any process.

The Admin Panel shares the Mini App's navy, blue, burgundy and gold brand
tokens, but deliberately remains a dense desktop operations interface. It has
no decorative or state-transition animations.

## Capabilities

### Current owner workflow (Admin 1.60.4)

The retired Broadcast test and Interesting facts screens are removed. Old facts
links open Publications; old broadcast links open Today. Legacy LIVE, Aurora and
Vault links open the matching subtab of the single Instant games section. Only
the selected game's summary is requested. Archive is the final navigation item.

Admin is static content served by the existing gateway, not a separate running
application service. A closed browser makes no Admin requests. Screens fetch on
entry and explicit actions; there is no periodic Admin API polling, including
the operational health screen, proposals and distribution delivery status.
Use Refresh data (or Refresh proposals in the editor section) to refresh.
Local clocks still enforce proposal expiry and show sales closing correctly.
System tabs request only their own data; the event feed combines its four
relevant sources. Project journals are fetched only in Development.

The legacy daily Interesting facts calculation is no longer registered or run
at API startup. Existing fact records remain untouched. Publication automation,
delivery, draw recovery and independent health/backup alerts continue running
without the Admin browser; they serve the actual project, not the Admin UI.
Schedule is a read-only, on-demand view and does not run a second scheduler.

- operational dashboard: version, uptime, database reachability, configured bot,
  scheduler state, counts, current funds, recent draws and ledger movements;
- multi-user player overview with balance, tickets, spent, won and net CAS;
- existing player search by name, username, Telegram ID or UUID, plus audited
  enable/disable control for five-ticket auto-play;
- setting a target player balance through an idempotent ledger adjustment;
- lottery ticket-price and base-jackpot configuration with an audit reason;
- separate current-jackpot adjustment through the immutable CAS ledger;
- current jackpots, central Kasper Fund and jackpot-win history;
- permanent read-only draw archive with results, funds, tickets, winners,
  timestamps and correlation IDs;
- immutable transaction ledger with date, type, user, lottery, draw and ticket
  filters;
- per-lottery number appearances, percentages, last appearance and draws since
  last appearance, calculated from completed draw history;
- lightweight ticket analytics overall and per lottery: total, active, settled
  and winning tickets, win percentage, participants, sales and payouts. The
  read model uses aggregate SQL and is cached for up to 60 seconds;
- permanent administrator audit history.
- protected project history with separate read-only CHANGELOG and DEVLOG tabs,
  including all previous versions. CHANGELOG follows product SemVer while
  DEVLOG additionally receives a stable `DEV-0001` sequence number;
- direct URLs and last-section memory, so refresh returns the owner to the same
  section instead of forcing the operational overview.

Schedule editing remains deliberately unavailable without effective-date rules.
Price and base jackpot are configuration for future draws. The current jackpot
may be adjusted separately with a mandatory reason; the mutation is row-locked
and creates both ledger and administrator audit records. Distribution balances
remain lifecycle-owned. Completed draws have no mutation endpoint.

## One-time credential setup

From the repository root:

```powershell
.venv\Scripts\python.exe -m scripts.configure_admin
```

The script asks for a username and a password of at least 12 characters. It
writes an Argon2 password hash and a randomly generated session secret directly
to ignored `.env`; neither the password, hash nor secret is printed.

Restart the backend after configuration. For a local non-Docker run, use two
terminals from the repository root.

Terminal 1:

```powershell
.venv\Scripts\Activate.ps1
alembic upgrade head
uvicorn k_loto.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_admin.ps1
```

## Security model

- incomplete credential configuration disables login;
- passwords are verified against an Argon2 hash;
- the signed session is short-lived, HttpOnly and SameSite Strict;
- production cookies are Secure;
- state-changing requests require a per-session CSRF token;
- no credential or session secret enters the frontend bundle;
- mutation services hold database row locks and commit CAS ledger plus audit
  records atomically;
- idempotency keys protect balance, reserve and jackpot adjustments from retries.

Rate limiting and production reverse-proxy policy remain deployment work and do
not weaken the current authentication boundary.

Project journals remain version-controlled Markdown files. The Admin API uses
a fixed file allowlist and never accepts a filesystem path from the browser.
They are rendered as text, so journal content cannot inject executable HTML.
The historical `0.x` entries remain unchanged. Starting with `1.0.0`, product
versions use `MAJOR.MINOR.PATCH`: minor for compatible features, patch for fixes,
and major only for an incompatible platform change.


## Owner dashboard — 1.19.0

The primary navigation is Overview, Lotteries, Schedule, Draws, Players,
Analytics and System. System owns service diagnostics, CAS ledger, notification
queue, audit and the Development tab (CHANGELOG/DEVLOG). The old /development URL
opens that tab. All displayed dates use Europe/Moscow.

The overview puts lifetime jackpot totals, the latest jackpot and the all-time
record together. Per-lottery rows combine current jackpots, lifetime wins/payouts,
latest jackpot amounts/draw links and ticket counts. Jackpot counts mean draws
with a jackpot payout, not winning tickets or unique players. Inactive lotteries
remain in the lifetime breakdown. The collapsible history contains the latest
50 events only; it never supplies lifetime maxima or per-lottery latest amounts.

Dashboard data refreshes on entry and on request. Ticket analytics may lag
by its existing 60-second server cache. Manual refresh preserves expanded history.
Responsive tables scroll within their panels instead of widening the entire page.
Draw details use JackpotWinEvent as evidence of a jackpot payout. They never infer
a win merely from the jackpot balance falling.

The 2026-09-05 SHADOW/FLASH audit is recorded in
[the read-only investigation](FAST_RANDOM_AUDIT_2026-09-05.md).
