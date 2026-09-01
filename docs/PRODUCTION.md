# Production operations

The owner-authorized VPS runs PostgreSQL, FastAPI/scheduler, Telegram bot, Caddy,
Telegram Mini App and Web Admin with Docker Compose in `/opt/k-loto`. The existing
sslip.io HTTPS endpoint and VPS are sufficient; no extra host or domain is
required. Port 9443 is used because the VPS VPN owns the standard TLS ports.

Before every schema release, run `scripts/backup_production.sh` and verify a
non-empty PostgreSQL custom-format dump in the private backup volume. Deployment
then uploads the reviewed repository, runs `docker compose build` and starts the
stack. The API container applies Alembic and the idempotent production bootstrap
before serving traffic.

Обычный выпуск выполняется из чистого commit одной командой:

```powershell
.\.venv\Scripts\python.exe scripts\release_vps.py
```

Для выпуска только изменённых сервисов можно указать, например,
`--services api bot` или `--services gateway`. Сценарий не печатает пароли и
сам создаёт backup до замены файлов. План без подключения проверяется ключом
`--dry-run`.

Резервная копия считается проверенной только после пробного восстановления в
одноразовую БД. На VPS команда запускается из `/opt/k-loto`:

```sh
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db \
  sh -s -- /backups/k-loto-YYYYMMDDTHHMMSSZ.dump < scripts/verify_backup_restore.sh
```

Сценарий принимает только путь вида `/backups/k-loto-*.dump`, проверяет ключевые
таблицы и всегда удаляет временную БД `k_loto_restore_check`. Рабочая база не
отключается и не изменяется.

Production must define `MINIAPP_URL`, bot token, database credentials and Admin
credentials and `OWNER_TELEGRAM_ID` in ignored `/opt/k-loto/.env.production`.
Caddy serves the Mini App
on `WEB_HOST` and Admin on `ADMIN_HOST`; `/api/*` proxies to FastAPI. PostgreSQL
is not published externally. Daily backups have 14-day retention.

After deployment verify container health, Alembic head, `/health`, both HTTPS
hosts, bot polling without conflicts, active lottery rows and jackpot balances.
Never print `.env.production` or Telegram tokens.
