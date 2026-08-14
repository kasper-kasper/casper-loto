# Telegram player bot

The aiogram 3.x bot is a transport adapter. `/start` idempotently binds the
Telegram identity to a backend user and displays the CAS balance. Ticket
purchase controls are intentionally absent: checkout belongs to the future
Mini App.

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
