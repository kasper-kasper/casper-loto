# Web Admin Panel

Milestone 6 provides a separate React/TypeScript interface at
<http://127.0.0.1:5174>. It is not embedded in Telegram and contains no lottery
or CAS business logic.

The local `5174` workflow is development-only. In the final deployment the
compiled Admin client will be served continuously by the HTTPS reverse proxy;
the owner will open its normal URL and log in without starting any process.

## Capabilities

- operational dashboard: version, uptime, database reachability, configured bot,
  scheduler state, counts, current funds, recent draws and ledger movements;
- multi-user player overview with balance, tickets, spent, won and net CAS;
- setting a target player balance through an idempotent ledger adjustment;
- lottery ticket-price and base-jackpot configuration with an audit reason;
- current jackpot/distribution visibility and reserve adjustment through ledger;
- permanent read-only draw archive with results, funds, tickets, winners,
  timestamps and correlation IDs;
- immutable transaction ledger with date, type, user, lottery, draw and ticket
  filters;
- per-lottery number appearances, percentages, last appearance and draws since
  last appearance, calculated from completed draw history;
- permanent administrator audit history.

Schedule and payout-configuration editing is deliberately unavailable while
Daily cutoff/payout decisions remain open. Current jackpot and distribution
balances are lifecycle-owned and cannot be silently overwritten. Completed
draws have no mutation endpoint.

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
- idempotency keys protect balance and reserve adjustments from retries.

Rate limiting and production reverse-proxy policy remain deployment work and do
not weaken the current authentication boundary.
