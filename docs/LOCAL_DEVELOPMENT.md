# Local browser development and Telegram tunnel

This workflow is intended for Windows and does not connect to the configured
VPS. Local scripts reject a non-loopback PostgreSQL hostname.

## One-time prerequisites

1. Install PostgreSQL 16 or newer from the official Windows installer:
   <https://www.postgresql.org/download/windows/>.
2. During installation keep port `5432` and remember the local `postgres`
   password.
3. In pgAdmin, create a login role named `k_loto` and a database named `k_loto`
   owned by that role. Use an alphanumeric password for an easy local URL.
4. In the repository `.env`, set a local URL only:

   ```env
   DATABASE_URL=postgresql+asyncpg://k_loto:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/k_loto
   ```

5. From the repository root install/update dependencies once:

   ```powershell
   .venv\Scripts\uv.exe sync --extra dev
   Set-Location frontend\miniapp
   npm install
   Set-Location ..\..
   ```

Node.js 22+ is required. The current development workspace may use the ignored
portable copy under `.tools`; a fresh machine can install Node.js LTS from
<https://nodejs.org/en/download>.

## Play in an ordinary browser

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\enable_local_dev.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start_local_dev.ps1
```

The first script safely updates only local development keys in the ignored
`.env` and generates a strong session secret without printing it. The second:

- refuses any non-local database hostname;
- applies Alembic migrations;
- starts API and Mini App in hidden child processes;
- opens <http://127.0.0.1:5173>;
- stops both children when you press `Ctrl+C`.

On first authenticated browser request the backend idempotently creates:

- `Local Test Player`;
- 100,000 test CAS;
- ЛСД-лото 5/20 and the unified three-slot Daily 4/15 game at 100 CAS per ticket;
- 10,000 CAS base jackpot and 100,000 CAS reserve;
- the next draw for all four lotteries.

All initial and later `+ TEST CAS` credits are immutable ledger transactions.
Repeated startup does not duplicate the initial credit or lottery entities.
The numbers above are development fixtures, not production business defaults.

Logs are stored in ignored `.tools/local-dev-logs`. Real Telegram tokens are
not needed for browser mode.

## Open the same UI inside Telegram without a domain

Cloudflare Quick Tunnels provide a temporary free HTTPS address. The address
changes whenever the tunnel restarts and is suitable only for testing.

1. Stop browser mode with `Ctrl+C`.
2. Disable the local bypass:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\disable_local_dev.ps1
   ```

3. Start the backend in terminal 1:

   ```powershell
   .venv\Scripts\Activate.ps1
   alembic upgrade head
   uvicorn k_loto.main:app --host 127.0.0.1 --port 8000
   ```

4. Start the Telegram-authenticated frontend in terminal 2:

   ```powershell
   Set-Location frontend\miniapp
   npm run dev:telegram
   ```

5. Start the tunnel in terminal 3 from the repository root:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\start_miniapp_tunnel.ps1
   ```

   On first run the script downloads `cloudflared.exe` from Cloudflare's
   official GitHub release into ignored `.tools`. It refuses to run if local
   bypass is enabled.

6. Copy the printed `https://...trycloudflare.com` URL into `.env`:

   ```env
   MINIAPP_URL=https://YOUR-TEMPORARY-NAME.trycloudflare.com
   ```

7. Restart the Telegram bot in terminal 4:

   ```powershell
   .venv\Scripts\Activate.ps1
   python -m bot
   ```

8. Send `/start` to the bot and press **Open K-Loto**. Telegram supplies signed
   `initData`; the local browser cookie bypass remains disabled.

Keep the frontend, API, tunnel and bot terminals open while testing. A new
tunnel run produces a new URL, so update `MINIAPP_URL` and restart the bot.

## Security boundary

Local browser mode is available only when all conditions hold:

- `APP_ENV=development`;
- `MINIAPP_DEV_AUTH_ENABLED=true`;
- a secret of at least 32 characters exists;
- client address and HTTP Host are loopback;
- session creation also has a loopback Origin.

Production returns `404` for session creation regardless of the bypass flag.
The cookie is HttpOnly, SameSite Strict, short-lived and scoped to Mini App API
paths. Never expose browser mode through a tunnel.
