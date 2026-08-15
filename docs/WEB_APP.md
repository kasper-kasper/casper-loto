# Player Web application

The ordinary browser client is a small alternative to Telegram gameplay. It
uses the same player, balance, Weekly/Daily draws, purchased tickets and immutable
results as the bot. The preserved Telegram Mini App is not involved.

## Features

- username/password login;
- current integer CAS balance and Weekly/Daily draw information;
- Weekly 5-of-20 or Daily 4-of-15 selection and purchase of 1 to 20 tickets;
- identical combinations in one purchase;
- active tickets and settled ticket history;
- completed draw result archive;
- logout and automatic session restoration.

Price, balance, draw assignment and purchase result are authoritative backend
values. Purchases use the matching transactional lottery service and a unique
idempotency key. The browser cannot write balances or draw results.

## Security

Every Web account belongs to exactly one regular `users` row. Passwords are
stored as Argon2 hashes. Authentication creates a signed, expiring HttpOnly,
SameSite cookie; production cookies are Secure. State-changing requests also
need the per-session CSRF token. `WEB_SESSION_SECRET` must be a separate random
secret of at least 32 characters and stays only in `.env` or the server secret
environment.

## Local start

Apply migrations and run the API first:

```powershell
.venv\Scripts\Activate.ps1
alembic upgrade head
uvicorn k_loto.main:app --reload
```

The player must already exist (send `/start` to the Telegram bot). In a second
terminal, create or reset that player's Web login; prompts hide the password:

```powershell
.venv\Scripts\python.exe -m scripts.configure_web_player
```

The command also creates `WEB_SESSION_SECRET` in ignored `.env` when missing.
Restart the API after the first configuration. Start the browser client:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_web.ps1
```

Open `http://127.0.0.1:5175`. Vite proxies `/api` to the local API, matching the
same-origin production topology. Account configuration is an operator setup
step, not an ordinary player action.
