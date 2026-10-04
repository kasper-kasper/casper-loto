## Unified VPS maintenance and important diagnostic retention — 2026-10-04

- Added one stdlib maintenance entry point with daily 05:00 MSK cleanup and hourly API/bot diagnostic capture. Compact policy for fewer than 50 players: 512 MB build-cache reserve with 48-hour minimum age; current/referenced images plus two tagged rollback versions, seven-day image age; newest three known rollback archives per category plus 14 days; known temporary uploads after 48 hours. Unknown files, dumps, symlinks, hardlinks and all Docker volumes are excluded.
- Financial ledger, balance movements, purchased tickets, draws and database audit history remain permanent. Diagnostic gzip copies are retained for 90 days, with private directories/files and per-container capture cursors. Failed capture aborts cleanup. API/bot Docker buffers use 20 MB × 5; gateway/database use 10 MB × 3. Save available logs before recreation and retain new-container logs hourly. Diagnostics are copies of available buffers, not a replacement for the permanent database ledger.
- Shared publication/maintenance flock and separate backup flock prevent overlap. General release helper now holds the lock throughout, marks rollback images and captures diagnostics before restarting; broad deployment-time pruning was replaced with scheduled maintenance. Existing daily 03:30 MSK database backup and 14-day dump retention remain intact. No business rule, schema, frontend or money changes.
- Local verification: focused lint/format, 13 isolated housekeeping regressions (12 passed; Windows symlink case requires Linux), release CLI dry run and Git whitespace checks. No purchase tests or transactions. Linux regression, systemd/Compose validation, backups, bounded-log recreation and production health checks accompany installation. Retention settings and growth/tuning instructions are documented in docs/SERVER_STORAGE.md and AGENTS.md.

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
- Playwright проверил пять фаз на ширинах 1440/1024/390/360: координаты покупки и высоты каждой секции неизменны между фазами, горизонтального overflow нет. Просмотрены скриншоты desktop, мобильного эфира и ручного PULSE. Дополнительно проверен компактный 1366×768: все три кнопки покупки видны без прокрутки. Артефакты локально в `.playwright-mcp/` и не входят в релиз.
- Добавлены регрессии вложенности эфира, сохранения DOM-сцены и ручных чисел после эфира. Релиз web-only: версия API остаётся 1.39.0, backend и база не изменены.
- Проверки: Ruff, format, mypy; 224 backend, 71 Mini App, 25 admin и 18 web тестов; lint/typecheck/build всех frontend. Общий запуск остановился на существующем нестабильном admin-тесте Escape (`amount=null`); ошибка повторилась в полном admin-наборе, изолированные два случая и последующий полный admin-набор прошли без изменений кода. Остальные шаги после остановки выполнены отдельно. Web console без ошибок, reduced-motion отключает анимацию.
- Production: `46d9182` опубликован через `release_vps.py --services gateway` после успешного backup. API/бот не перезапускались, API/DB healthy, публичный `/health` — 200. JS/CSS побайтово совпадают со сборкой. После публикации просмотрены production-скриншоты 1366×768 и 390×844: три встроенных эфира, ноль нижних панелей, без horizontal overflow и ошибок console. Локальный preview закрыт; реальных покупок в ходе проверки не было.

## [1.39.0] - 2026-09-21

- Fast web вынесен в отдельный компонент с тремя стабильными колонками и локальными live-потоками. Покупка случайного билета — один существующий API-запрос; ручной выбор раскрывается без модального перехода. Проверяются текущий тираж/цена, баланс и закрытие продаж; неопределённая покупка сохраняется в sessionStorage по UUID игрока и игре, повтор использует тот же ключ/числа. Смена тиража или цены блокирует автоматическую новую покупку до проверки пользователем.
- Новая графика создана встроенным imagegen: отдельные FLASH, CODE, PULSE; production JPEG всего около 503 KB. Промпты и происхождение: `docs/FAST_WEB_ART.md`. Старые Fast-сцена и общий крупный SVG-пульс web удалены; остальные экраны не редизайнились.
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
