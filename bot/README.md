# Telegram player bot

The aiogram 3.x bot is the primary player interface. `/start` idempotently binds
the Telegram identity and opens balance, Weekly purchase, ticket history,
results, statistics and rules. Weekly checkout supports random numbers,
identical combinations and an atomic multi-ticket cart. Handlers contain no CAS
or lottery mathematics; they call the same application services as other
clients.

After a committed ticket purchase or Weekly settlement, the bot delivers a
durable outbox event. Unique event keys and terminal `SENT` records protect
normal retries from sending the same event twice. Failed and interrupted
deliveries are retried without repeating purchase or settlement logic.

Apply migrations and run from the repository root:

```powershell
alembic upgrade head
python -m bot
```

`LOTTERY_BOT_TOKEN` and `DATABASE_URL` must exist only in the local `.env` or
runtime secret store.
