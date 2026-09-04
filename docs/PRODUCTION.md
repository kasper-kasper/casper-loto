# Production operations

The owner-authorized VPS runs PostgreSQL, FastAPI/scheduler, Telegram bot, Caddy,
Telegram Mini App and Web Admin with Docker Compose in `/opt/k-loto`. The existing
sslip.io HTTPS endpoint and VPS are sufficient; no extra host or domain is
required. Port 9443 is used because the VPS VPN owns the standard TLS ports.

Перед каждым выпуском сценарий создаёт PostgreSQL backup. Web-интерфейсы
компилируются локально и отправляются на VPS уже готовыми: малый сервер больше не
запускает одновременно TypeScript/Vite и не упирается в память. Backend при
необходимости по-прежнему собирается на VPS. На сервере настроен swap 2 ГБ как
страховка от редких пиков; в обычной работе он не используется.

Обычный выпуск выполняется из чистого commit одной командой:

```powershell
.\.venv\Scripts\python.exe scripts\release_vps.py
```

Для выпуска только изменённых сервисов можно указать, например,
`--services api bot` или `--services gateway`. Сценарий не печатает пароли,
показывает каждый этап, ограничивает время зависшей операции и сам создаёт backup
до замены файлов. Для `gateway` он собирает Mini App и Admin на локальном
компьютере, а на VPS формирует только лёгкий Caddy-образ. План без подключения
проверяется ключом `--dry-run`.

Обычное визуальное обновление публикуется так:

```powershell
.\.venv\Scripts\python.exe scripts\release_vps.py --services gateway
```

Проверка списка backup через `pg_restore --list` выполняется при backend-релизе.
Полное пробное восстановление остаётся отдельной периодической проверкой: оно не
нужно при каждой правке CSS или текста.

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
