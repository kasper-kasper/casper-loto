# Player Web application

The ordinary browser client is a small alternative to Telegram gameplay. It
uses the same player, balance, Weekly/Daily draws, purchased tickets and immutable
results as the bot. The preserved Telegram Mini App is not involved.

## Features

- one-click login from the player's private Telegram bot chat;
- optional username/password fallback;
- current integer CAS balance and Weekly/Daily draw information;
- always-visible current Weekly/Daily jackpots with automatic refresh;
- Weekly 5-of-20 or Daily 4-of-15 selection and purchase of 1 to 20 tickets;
- identical combinations in one purchase;
- active tickets and settled ticket history;
- completed draw result archive;
- logout and automatic session restoration.

Price, balance, draw assignment and purchase result are authoritative backend
values. Purchases use the matching transactional lottery service and a unique
idempotency key. The browser cannot write balances or draw results.

## Security

The primary login flow issues a five-minute one-time token to the already bound
Telegram player. Only its SHA-256 hash is stored; the raw value travels in a URL
fragment, so it is not sent in HTTP request URLs or access logs. Atomic
consumption prevents a second use. The resulting signed, expiring HttpOnly
SameSite cookie is independent of Telegram. Production cookies are Secure and
state-changing requests also need the per-session CSRF token.

Password login remains an optional fallback. Every password Web account belongs
to one regular `users` row and uses an Argon2 hash. `WEB_SESSION_SECRET` remains
separate and private.

## Production login

1. Send `/start` or `/web` to the K-Loto bot.
2. Press **🌐 Открыть Web-версию**, then **🌐 Войти и играть**.
3. The player site opens under that exact Telegram account without a password.

Opening a link from another Telegram account switches the browser session to
that account. An unused link expires after five minutes.

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
