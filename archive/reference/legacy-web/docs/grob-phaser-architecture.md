# Архитектура web-версии «ГРОБ» на Phaser 3

Статус: архитектурное решение для последующей реализации. Дата исследования:
23 сентября 2026 года. Область изменения: только пользовательский web frontend,
только лотерея `grob`. Этот документ не является реализацией.

## Краткое решение

«ГРОБ» следует превратить в лениво загружаемый полноэкранный Phaser 3 experience
внутри существующего React-приложения `archive/reference/legacy-web/frontend/web`. React сохраняет
аутентификацию, каталог, навигацию, API-клиент, серверные данные и оркестрацию
покупок. Phaser владеет видимой игровой сценой, вводом внутри неё, 2D-анимацией,
эффектами и эфиром. Между ними нужен небольшой типизированный bridge; Phaser не
обращается к `fetch` и не рассчитывает игровые правила.

Новый backend-контракт для первой версии не нужен. Существующие
`GET /dashboard`, `POST /lotteries/grob/purchases` и
`GET /live?scope=standard&lottery_code=grob` уже покрывают каталог, покупку,
серверную временную шкалу эфира и результат. Ручная покупка отправляет ровно одну
выбранную комбинацию. Быстрые x1/x5/x25 отправляют соответственно 1, 5 или 25
случайных комбинаций одним атомарным запросом и всегда используют
`draw_count: 1`. Значение `draw_count: 5` означает пять разных тиражей и не имеет
отношения к кнопке быстрой покупки x5.

## 1. Что обнаружено в текущем проекте

### Структура и сборка

- Репозиторий содержит три отдельных frontend-приложения: `archive/reference/legacy-web/frontend/web`,
  `frontend/miniapp` и `frontend/admin`, а также FastAPI/SQLAlchemy backend в
  `backend`.
- Нужная область — `archive/reference/legacy-web/frontend/web`: React 19, TypeScript 5.9, Vite 7, Vitest и
  Testing Library. Phaser и клиентский роутер сейчас не установлены.
- Web собирается отдельной стадией в `frontend/Dockerfile` и публикуется Caddy
  как статический SPA под `/web/`. API доступен на том же origin по
  `/api/v1/web`.
- `archive/reference/legacy-web/frontend/web/src/main.tsx` монтирует один `App` под `StrictMode`. Это важно:
  Phaser host обязан выдерживать development mount → cleanup → повторный mount
  без второго canvas, таймеров и слушателей.
- Маршрутизации по URL сейчас нет. `App.tsx` переключает представления локальным
  `view` (`lotteries`, `fast`, `live`, `tickets`, `profile`) и открывает игры
  состоянием `picker`.
- Каталог находится в `Experience.tsx`; он получает готовый массив лотерей и
  вызывает `onOpen(lottery)`. Для `grob` `App.tsx` сейчас делает ранний return в
  полноэкранный `GrobGame`.
- Сессия использует Secure/HttpOnly cookie, CSRF-токен хранится внутри
  `archive/reference/legacy-web/frontend/web/src/api.ts`, а запросы выполняются с `credentials: "include"`.
- `App.tsx` синхронизирует локальные часы с `Dashboard.server_time`, обновляет
  dashboard/account через 30 секунд (через 5 секунд в live/Fast) и при возврате
  вкладки в foreground.
- Текущий grob-арт `archive/reference/legacy-web/frontend/web/src/assets/grob/crypt-environment.png` весит
  примерно 1,99 МБ. `App.tsx` дополнительно импортирует grob-арт из дерева
  Mini App, из-за чего Docker web-сборка специально копирует miniapp assets.
  Новая сцена должна иметь собственный web asset bundle и не усиливать эту
  связь.

### Сервер и источники истины

- Web API переиспользует `MiniAppQueryService`; данные Telegram Mini App и web
  относятся к одним пользователям, балансам, билетам, тиражам и ledger.
- `DashboardResponse` уже содержит `server_time`, баланс и для каждой лотереи:
  `ruleset_code`, размеры полей, цену, джекпот, номер/время тиража,
  `sales_close_at`, `purchase_available`, `sales_status`, число билетов игрока и
  лимит покупки.
- Покупка проходит через `LotteryTicketPurchaseService`, транзакцию БД, блокировки
  и неизменяемый ledger. Ключ идемпотентности восстанавливает исходный результат
  (`already_processed=true`) и не создаёт повторное списание.
- `GET /api/v1/web/live` принимает `lottery_code`. При `grob` он возвращает только
  соответствующие completed/next draw, серверное время, immutable winning
  numbers, `live_starts_at`, массив `reveal_at`, `live_ends_at`, количество
  билетов игрока, сумму выигрыша и до трёх выделенных билетов.
- Сервер начинает визуальную временную шкалу не раньше фактического
  `executed_at`. Для обычной лотереи числа раскрываются с шагом две секунды.
  Клиент должен воспроизводить эти timestamps, а не запускать собственный
  «случайный тираж».

## 2. Как сейчас реализована лотерея «ГРОБ»

### Механика

Серверная конфигурация `grob_3_16` — три уникальных числа из 1–16, билет 6 666
CAS, два ежедневных тиража в 06:06 и 23:06 МСК, закрытие продаж за две минуты.
Совпадения 1/3 и 2/3 дают фиксированные выплаты, 3/3 делит джекпот. Все денежные
операции и расчёты уже находятся на backend и не должны переноситься в сцену.

### Web UI

- `archive/reference/legacy-web/frontend/web/src/GrobGame.tsx` — полноэкранный React/CSS экран с фоновой PNG,
  HTML-сеткой из 16 кнопок, количеством билетов, переключателем пяти тиражей и
  кнопкой покупки. Это стилизованный dashboard, а не игровая сцена.
- `App.tsx` также содержит старый `GrobPicker`. В обычном пути он фактически
  недостижим, потому что раньше него срабатывает ранний return с `GrobGame`.
  В тексте этого старого компонента ошибочно упоминаются шесть чисел, хотя
  серверный формат и актуальный `GrobGame` используют три. При миграции этот
  дубликат следует удалить, не переносить.
- После покупки `GrobGame` вызывает общий `bought`, который закрывает игру,
  показывает toast в каталоге и перезагружает dashboard. Это противоречит новому
  требованию немедленно показать новый пустой билет внутри игры.
- Случайная кнопка сейчас только заполняет ручной билет. Отдельных однонажатийных
  x1/x5/x25 нет.
- Неопределённый сетевой результат не переживает reload: текущий grob хранит
  idempotency key только в `useRef`. Более надёжный шаблон уже реализован в
  `Fast.tsx`: pending attempt сохраняется в `sessionStorage` до отправки и
  повторяется с тем же ключом.
- `GrobLiveStage` находится в `App.tsx` внутри общей вкладки «Эфир». Это React/CSS
  композиция; общий live poll запрашивает все standard-лотереи и выбирает один
  ближайший эфир. Поэтому отдельный эфир «ГРОБ» не является частью текущего
  игрового клиента.
- `styles.css` содержит несколько поколений grob-стилей: старый modal, live room
  и новый fullscreen layout. После миграции их нужно удалить только после
  визуального parity/smoke-теста, чтобы не оставить мёртвый CSS.

## 3. Какие API и существующие модули необходимо сохранить

Сохраняются без изменения бизнес-смысла:

| Контракт/модуль | Назначение в новой сцене |
|---|---|
| `webApi.session()` | существующая web-аутентификация и получение CSRF |
| `webApi.dashboard()` | серверный формат `grob`, баланс, цена, лимиты, открытость продаж, серверные часы |
| `webApi.purchase("grob", combinations, key, 1)` | единственная команда покупки ручного или быстрого набора |
| `webApi.live("standard", "grob")` | отдельный feed «ГРОБ», серверная временная шкала и результат |
| `webApi.tickets()` | существующая история/проверка билетов после неоднозначной ошибки |
| `Lottery`, `LiveDraw`, `LiveFeed`, purchase response types | базовые DTO; типы следует дополнить реально возвращаемыми полями, а не создавать параллельные модели |
| `LotteryTicketPurchaseService` | проверка комбинаций, лимитов, средств, cutoff, транзакция и ledger |
| `MiniAppQueryService.dashboard/live` | единый query source для web и Mini App |
| `domain/lottery_rules.py` и `grob_3_16` | единственный источник математики и settlement |
| `domain/live_timeline.py` | единственный источник моментов reveal |

Не следует создавать `/grob/*` API только ради Phaser. Возможное расширение API
допустимо лишь если во время реализации обнаружится невозможность безопасно
восстановить конкретную pending-покупку; это не требуется для базовой версии.

## 4. Предлагаемая архитектура новой версии

```text
React App (session, catalog, account, navigation)
  └─ GrobExperienceHost (lazy boundary, lifecycle, accessibility)
      ├─ useGrobExperience / reducer (presentation state + async orchestration)
      ├─ GrobApiAdapter (existing webApi only)
      ├─ GrobBridge (typed intents down/up)
      └─ Phaser.Game
          ├─ GrobBootScene
          ├─ GrobPreloadScene
          ├─ GrobPlayScene
          ├─ GrobLiveScene
          └─ GrobOverlayScene

existing /api/v1/web
  ├─ GET /dashboard
  ├─ POST /lotteries/grob/purchases
  └─ GET /live?scope=standard&lottery_code=grob
```

`GrobExperienceHost` загружается через `React.lazy`/dynamic import только после
выбора `grob`. Сам модуль Phaser также не должен попадать в initial catalog
chunk. Host создаёт один controller, один bridge и один `Phaser.Game` на DOM
container, а при выходе полностью уничтожает их.

State reducer/controller — тонкий application layer именно для клиентского
experience. Он не содержит цены, лимитов, выигрышной математики или расписания:
это приходит в DTO. Он отвечает только за выбор чисел, команды пользователя,
pending/retry, clock offset и отображаемую фазу.

## 5. Где проходит граница React / Phaser

### React владеет

- сессией, CSRF, login/logout;
- входом из каталога и выходом обратно, history/focus integration;
- загрузкой Phaser chunk и внешним loading/error boundary;
- dashboard/live polling, AbortController и revalidation;
- выполнением purchase promise и сохранением pending attempt;
- серверным snapshot состояния, clock offset и reducer;
- обновлением общего баланса/account после покупки;
- визуально скрытыми доступными контролами и `aria-live` сообщениями;
- fallback-экраном, если canvas/WebGL/asset preload не запустились.

### Phaser владеет

- всей видимой центральной игровой композицией;
- 16 интерактивными объектами выбора, готовым билетом и быстрыми x1/x5/x25;
- pointer/keyboard focus visuals внутри canvas;
- камерой, слоями, спрайтами, таймлайнами, частицами, светом и audio cues;
- переходами play ↔ waiting ↔ live ↔ result;
- отображением immutable snapshot, полученного через bridge.

React не должен рисовать поверх canvas сетку карточек или основную панель
покупки. Допустимы только оболочка/кнопка выхода, loading/error recovery,
невидимый accessibility mirror и аварийный fallback. Phaser не должен импортировать
`webApi`, читать cookie/CSRF, самостоятельно poll-ить сервер или изменять React
state напрямую.

Существующий URL-router вводить только ради этой задачи не требуется. В первой
версии сохраняется текущий `picker`-flow, но вместо раннего return на
`GrobGame.tsx` монтируется `GrobExperienceHost`. Deep link можно добавить позже
отдельным решением, не смешивая его с игровой миграцией.

## 6. Phaser lifecycle

1. React проверяет сессию и перед открытием получает свежий dashboard.
2. Если `grob.purchase_available`/формат доступны, показывается lightweight
   loading shell и начинается dynamic import grob chunk.
3. Host один раз создаёт controller/bridge, затем `new Phaser.Game(config)` с
   `parent` на конкретный container. В StrictMode создание защищается ref-guard,
   cleanup всегда симметричен.
4. `GrobBootScene` задаёт минимальную конфигурацию, device capabilities,
   animation/audio preferences и запускает core preload.
5. `GrobPreloadScene` грузит только core pack, отдаёт прогресс через bridge и
   при успехе запускает `GrobPlayScene` + `GrobOverlayScene`.
6. React передаёт первый `GrobSnapshot`; сцены никогда не стартуют со
   «встроенной» ценой или номером тиража.
7. ResizeObserver сообщает размер container; layout service перестраивает
   camera/world zones, hit areas и safe-area отступы.
8. При входе в live лениво подгружается `grob-live` pack, после чего запускается
   `GrobLiveScene`. Core selection textures остаются только если нужен быстрый
   возврат.
9. На `visibilitychange` controller немедленно revalidate-ит dashboard/live и
   пересчитывает фазу по server clock; Phaser не «догоняет» пропущенные tweens, а
   сразу отображает правильное число раскрытых символов.
10. На unmount: abort запросов, остановка polling, unsubscribe bridge, остановка
    audio/timers/tweens, `scene.shutdown`, удаление загруженного live pack,
    `game.destroy(true)`, очистка refs. Никаких глобальных listener после выхода.

Конфигурация renderer: `Phaser.AUTO` (WebGL при возможности, Canvas fallback),
antialias для обычной графики, прозрачность отключена, DPR ограничен разумным
порогом (рекомендуемо 1.5, максимум 2 после профилирования). Ошибка WebGL не
должна блокировать Canvas renderer.

## 7. Структура сцен

### `GrobBootScene`

Минимальная сцена без тяжёлых assets: проверяет renderer, читает переданные
preferences, регистрирует animation keys и запускает preload. Не обращается к
API.

### `GrobPreloadScene`

Показывает тематический, но лёгкий индикатор. Загружает core atlas, bitmap/web
fonts, фон, UI sounds. Обрабатывает `loaderror`; обязательный asset failure
переводит React boundary в fallback, необязательный эффект просто выключается.

### `GrobPlayScene`

Основная игровая комната. Здесь находится окружение, ticket object, 16 объектов
выбора, ручная покупка и быстрые x1/x5/x25. UI должен быть частью мира/алтаря, а
не прямоугольной HTML-панелью. Scene лишь эмитит intents и визуализирует snapshot.

### `GrobLiveScene`

Отдельная постановка эфира: waiting room, начало, последовательный reveal и
финальный win/loss. Она получает `LiveDraw` с серверными timestamp и не генерирует
числа. Ее assets загружаются отдельным pack.

### `GrobOverlayScene`

Phaser HUD поверх активной play/live scene: баланс, номер/время тиража, mute,
back, короткие статусы и non-blocking error/retry. Overlay не содержит бизнес-
логики. Кнопка back также должна иметь React/DOM fallback для доступности.

Не следует создавать отдельную Phaser Scene для каждого reducer-state: это
приведёт к лишним перезапускам и загрузкам. Play и Live — устойчивые сцены, а
подфазы меняются внутри них по snapshot.

## 8. State machine / состояния

Рекомендуется обычный дискриминированный TypeScript reducer, без XState: автомат
линеен и не оправдывает ещё одну runtime-зависимость.

| Фаза | Условие/содержимое | Разрешённые переходы |
|---|---|---|
| `loading` | chunk, core assets или initial dashboard ещё грузятся | `idle`, `error` |
| `idle` | пустой билет, продажи открыты | `selecting`, `purchasePending`, `drawWaiting`, `error` |
| `selecting` | выбрано 1–2 числа | `idle`, `ready`, `drawWaiting` |
| `ready` | выбрано ровно 3 валидных числа | `selecting`, `purchasePending`, `drawWaiting` |
| `purchasePending` | сохранён attempt, ввод заблокирован | `purchaseSuccess`, `purchaseUncertain`, `purchaseError` |
| `purchaseSuccess` | короткая подтверждающая анимация с ответом сервера | `idle` с новым пустым билетом |
| `purchaseUncertain` | запрос мог дойти; attempt сохранён | retry того же attempt, reconcile, `error` |
| `purchaseError` | окончательная 4xx либо безопасная preflight-ошибка | назад в предыдущую редактируемую фазу |
| `quickPending` | вариант `1 | 5 | 25`, комбинации уже заморожены | те же ветви, что purchase pending |
| `drawWaiting` | продажи закрыты/следующий эфир ещё не начался | `liveStarting`, `idle` нового тиража, `reconnecting` |
| `liveStarting` | `now >= live_starts_at`, результат ещё может готовиться | `liveReveal`, `reconnecting` |
| `liveReveal` | раскрыто `count(reveal_at <= serverNow)` чисел | `result`, `reconnecting` |
| `result` | win/loss/spectator по server response | `idle` следующего тиража, replay summary |
| `reconnecting` | live poll временно недоступен | предыдущая вычисленная фаза, `error` |
| `error` | fatal bootstrap/asset/auth error | retry, exit to catalog/login |

Состояния `quick x1`, `x5`, `x25` — payload `quickPending.quantity`, а не три
копии логики. `purchaseSuccess` может длиться коротко (например, 600–900 мс), но
новый пустой билет должен быть создан автоматически, без modal/подтверждения и
без закрытия experience.

Reducer обязан игнорировать устаревшие ответы по `requestId`/`draw_number`. При
смене draw selection сбрасывается, если он ещё не был отправлен. Отправленный
attempt остаётся immutable до однозначного исхода.

## 9. Data flow

```text
dashboard/live HTTP response
       ↓ normalize + server clock offset
Grob controller/reducer ── snapshot ──→ bridge ──→ Phaser render
       ↑                                      │
       └── typed intent ←── bridge ←──────────┘
                    ↓
          preflight / purchase / retry
                    ↓
       purchase response + dashboard revalidate
```

Snapshot должен быть serializable и неизменяемым с точки зрения сцены. Минимум:

- `phase`, `selectedNumbers`, `selectedCount`;
- `lottery` (только нужные display-поля текущего server DTO);
- `balance`, `serverNow`, `salesOpen`, `canAfford`;
- `purchase` (`mode`, `quantity`, `cost`, `attemptId`, error/status);
- `live` (`draw`, reveal count/numbers, result kind);
- `preferences` (`reducedMotion`, `muted`, quality tier);
- monotonically increasing `revision`.

Phaser применяет snapshot только если revision новее. Он может проиграть
переходную анимацию, но конечное визуальное состояние всегда выводится из
snapshot. Ни Texture, ни GameObject не попадают обратно в React state.

## 10. Phaser ↔ React bridge

Bridge должен быть instance-scoped и типизированным, не `window` events и не
глобальный singleton.

```ts
type GrobIntent =
  | { type: "TOGGLE_NUMBER"; value: number }
  | { type: "BUY_MANUAL" }
  | { type: "BUY_QUICK"; quantity: 1 | 5 | 25 }
  | { type: "RETRY_PURCHASE" }
  | { type: "OPEN_LIVE" }
  | { type: "EXIT" }
  | { type: "SET_MUTED"; muted: boolean };

interface GrobBridge {
  publish(snapshot: GrobSnapshot): void;
  subscribeSnapshot(listener: (value: GrobSnapshot) => void): Unsubscribe;
  emitIntent(intent: GrobIntent): void;
  subscribeIntent(listener: (value: GrobIntent) => void): Unsubscribe;
  dispose(): void;
}
```

Сцена эмитит намерение, controller валидирует его против актуального snapshot,
выполняет side effect и публикует новое состояние. Защитные проверки должны быть
и в controller, и на сервере; disabled sprite не является защитой.

Для accessibility host создаёт visually-hidden DOM buttons/fieldset с теми же
командами, синхронизированными со snapshot, и `aria-live` для покупки/reveal.
Это не видимый HTML dashboard, а клавиатурный/screen-reader fallback. Phaser
также поддерживает Tab/стрелки/Enter через собственный focus model.

## 11. API interaction

### Initial load и синхронизация

1. Использовать уже загруженный dashboard для мгновенного skeleton.
2. Непосредственно перед разрешением покупки выполнить fresh dashboard.
3. Вычислить `clockOffset = Date.parse(server_time) - Date.now()`; для всех
   cutoff/reveal сравнений использовать `Date.now() + clockOffset`.
4. Poll dashboard: 30 секунд в спокойном play; 5 секунд возле cutoff/в waiting;
   немедленно при `visibilitychange` в foreground и после purchase.
5. Poll grob live отдельно: 15 секунд далеко от эфира, 3 секунды в окне
   ожидания/эфира, немедленно при foreground. Интервалы уточнить профилированием,
   не запускать параллельные запросы.

Каждый poll имеет AbortController, single-flight guard и sequence number.
Нельзя позволять медленному старому ответу перезаписать новый draw. `api.ts`
следует расширить опциональным `signal`; фиксированный `AbortSignal.timeout`
можно объединить с lifecycle abort через `AbortSignal.any`, если целевые браузеры
поддерживаются, либо маленький helper.

### Ошибки HTTP

- `401/403`: завершить experience, обновить session/показать login; CSRF не
  обходить.
- `402`: окончательная ошибка «Недостаточно CAS», pending очистить.
- `409`: продажи закрылись; pending очистить, обновить dashboard, перейти waiting.
- `422`: окончательная ошибка payload/правил; pending очистить, логировать без
  секретов, обновить формат.
- `429`: временная ошибка; уважать задержку, сохранить attempt, не спамить retry.
- `5xx`, timeout, offline: исход неоднозначен; attempt сохраняется.

## 12. Purchase flow

### Ручной билет

1. Игрок выбирает три уникальных числа 1–16 в Phaser.
2. На третьем числе state становится `ready`; кнопка покупки активна только при
   открытых продажах и достаточном балансе.
3. Нажатие покупает сразу — никакого confirmation modal.
4. Controller делает preflight fresh dashboard и проверяет тот же `draw_number`,
   цену, формат, cutoff и `purchase_available`.
5. Создаётся immutable attempt:
   `{key, userId, lotteryCode:"grob", drawNumber, price, mode:"manual",
   combinations:[[...selected]], drawCount:1, createdAt}`.
6. Attempt сначала записывается в `sessionStorage` под ключом с `user_id`, затем
   отправляется `webApi.purchase`.
7. Во время запроса все purchase controls блокируются; ambient animation может
   продолжаться.
8. При успехе используются `balance_after`, `ticket_ids`, `total_cost` и
   `already_processed`; attempt удаляется, проигрывается success, затем selection
   автоматически очищается. Experience остаётся открыт.
9. Параллельно revalidate dashboard, не заменяя подтверждённый `balance_after`
   более старым ответом.

Idempotency key переиспользуется только для байт-в-байт того же attempt. При
изменении выбранных чисел/quantity создаётся новый key. Двойной pointer event,
Enter и повторный React render блокируются одним controller single-flight.

### Неоднозначный результат

Если после отправки получен timeout/offline/5xx, показывается «Ответ не получен»
и безопасный retry с тем же payload/key. Пока draw/цена не изменились, retry
идемпотентен. Если draw сменился, нельзя повторно отправлять старую попытку:
первый запрос мог не зафиксироваться, и существующий API без `target_draw_id`
тогда купит уже следующий draw. Нужно заблокировать новую покупку, дать ссылки
«Проверить билеты» и «Я проверил — разрешить новую покупку», как в Fast flow.

## 13. Quick purchase x1 / x5 / x25

Кнопки видимы в Phaser и выполняют покупку одним нажатием без предварительного
показа/подтверждения комбинаций.

- x1 создаёт одну случайную комбинацию, x5 — пять, x25 — двадцать пять.
- Каждая комбинация содержит три разных числа 1–16 и сортируется только для
  отображения/стабильного payload. Разные билеты могут иметь одинаковую
  комбинацию: это разрешено существующей механикой.
- Использовать Web Crypto и unbiased `randomBelow` с rejection sampling;
  `Math.random` и modulo bias не использовать.
- Комбинации генерируются один раз до записи attempt. Retry никогда не генерирует
  новый набор.
- Один API вызов: `combinations.length === quantity`, `draw_count === 1`. Это
  даёт одну атомарную ledgered покупку и один idempotency key.
- Цена в сцене вычисляется для отображения как server `ticket_price * quantity`,
  но окончательная проверка/списание только серверные. Кнопка disabled при
  `balance < displayedCost`, однако backend остаётся авторитетным.
- Проверить `quantity <= max_tickets_per_purchase` и будущий per-player limit по
  ответу/preflight. Текущий grob limit (1000) допускает x25, но не hardcode его.
- Успех показывает количество купленных билетов и сразу возвращает новый пустой
  ручной билет.

Не использовать существующий `draw_count: 5` для quick x5. Возможность «на пять
тиражей» остаётся в backend, но не включается в новый основной UX, поскольку
заданная механика описывает ручной билет и быстрые количества билетов. Если
владелец захочет вернуть multi-draw, это отдельная явно подписанная команда.

## 14. Live draw architecture

Внутри grob experience есть переход в его собственный эфир; запрос всегда
`webApi.live("standard", "grob")`, а не общий standard feed. Выбор draw:

- если `latest_completed` ещё находится до `live_ends_at`, показывать его;
- иначе показывать `next_scheduled`;
- после завершения сохранять summary последнего результата до появления
  следующего актуального snapshot.

Фаза вычисляется исключительно по server-adjusted now и полям ответа:

- до `live_starts_at` — waiting/countdown;
- после старта, но без результата/reveal — starting/reconnecting ambience;
- `revealCount = count(reveal_at <= serverNow)`;
- показывать только первые `revealCount` элементов `winning_numbers`;
- после `live_ends_at` — result;
- win: `player_total_prize > 0`;
- loss: `player_ticket_count > 0 && player_total_prize === 0`;
- spectator: `player_ticket_count === 0`.

Анимация reveal может быть богаче, чем CSS, но timestamp и число всегда
серверные. При позднем входе сразу показать уже раскрытые числа и анимировать
только будущие. При background/lag не проигрывать длинную очередь устаревших
эффектов. `highlighted_tickets` использовать для итоговой карточки/подсветки
совпадений; не вычислять выигрыш на клиенте.

Live asset pack грузить при явном входе в эфир или незадолго до
`live_starts_at`. Ошибка pack не должна скрыть фактические числа: нужен упрощённый
Phaser text/shape fallback, а если не работает renderer — доступный DOM result.

## 15. Responsive behaviour

Canvas занимает размер fullscreen host, включая `100dvh`; safe areas учитываются
через CSS custom properties/host insets. Рекомендуется `Phaser.Scale.RESIZE` и
layout service, который размещает зоны заново, а не просто масштабирует один
desktop screenshot.

Три композиционных режима:

- wide (`>= 1180`): окружение/главный объект слева, интерактивный алтарь справа,
  но оба являются единой сценой с глубиной и анимацией;
- compact (`760–1179`): центральный объект сверху/в глубине, ticket и controls в
  нижней части canvas;
- mobile (`< 760`): вертикальная постановка, 4×4 интерактивные объекты, крупные
  touch targets минимум 44 CSS px и минимальный текст без browser zoom.

Пересчёт выполняется на ResizeObserver, orientation change и fullscreen changes.
Не перезагружать textures и не пересоздавать `Phaser.Game` при breakpoint.
Камера и hit areas обновляются вместе. Проверить 320×568, 390×844, 768×1024,
1366×768, 1920×1080 и zoom 200%.

## 16. Asset pipeline

Создать независимые packs `core` и `live`:

- core: оптимизированный фон, atlas интерактивных объектов/UI, минимальные FX,
  bitmap/font assets, короткие UI sounds;
- live: саркофаг/механизм reveal, дополнительные FX, result assets и live audio.

Рекомендации:

- WebP для фоновых/растровых Phaser textures; AVIF использовать только после
  реального browser/loader smoke и с WebP fallback;
- sprite sheets/texture atlases с trim и extrude; один-два атласа на pack вместо
  десятков запросов;
- SVG допустим для простых статичных знаков, но интерактивные raster textures
  лучше заранее растрировать в нужных scale variants;
- не встраивать текст/числа в изображения — Phaser text/bitmap font позволит
  локализацию, доступность и серверные значения;
- хранить source/master отдельно от production exports; коммитить только
  оправданные production assets и документировать происхождение/лицензию;
- budget первого core transfer ориентировочно до 1,5–2 МБ compressed, live pack
  до 1,5 МБ; точные budgets закрепить после art spike и измерять в build output;
- заменить текущую 1,99 МБ PNG на WebP/atlas только после визуального сравнения.

Vite imports дают content hashes. Pack manifests должны быть статически
типизированы/импортированы, чтобы Vite видел assets при build. Не строить runtime
URL строками, которые bundler не может обнаружить.

## 17. Performance strategy

- Dynamic import всего grob/Phaser chunk; каталог, login и другие игры не должны
  оплачивать его весом/parse time.
- `Phaser.AUTO`, Canvas fallback, DPR cap и quality tier по renderer/device,
  подтверждённые профилированием, а не user-agent sniffing.
- Preload только core; live и optional audio — отдельно.
- Ограниченный particle pool, без бесконечного создания объектов; emissive/light
  effects не должны зависеть от десятков dynamic lights.
- Переиспользовать GameObjects/tweens для 16 элементов и reveal slots.
- Остановить декоративные tweens/particles при `document.hidden`; polling также
  замедлить, но сделать немедленный sync при foreground.
- Не делать allocation/fetch в Phaser `update()`; snapshots применяются по
  событиям.
- Удалять live textures/audio после выхода из experience либо при memory
  pressure; весь cache гарантированно удаляется через `game.destroy(true)`.
- Проверить production build chunk sizes, first interaction latency, memory до/
  после десяти входов-выходов, long tasks и стабильные 60 FPS на среднем desktop;
  quality fallback 30 FPS допустим для слабых устройств.
- Canvas context lost/restored обрабатывать: пауза, сообщение, попытка restore;
  при провале предложить Canvas/fallback reload.

`prefers-reduced-motion` отключает camera shake, вспышки, parallax, частицы и
длинные переходы; состояния и reveal остаются понятными через мгновенную смену и
контраст. Настройка «Уменьшить движение» внутри игры может дополнять системную.

### Audio

Audio необязателен для первой поставки. Если добавляется, отдельный
`GrobAudioManager` запускается только после пользовательского gesture, имеет
mute по умолчанию до разблокировки, сохраняет выбор локально, при hidden плавно
останавливает ambience и уничтожается с game. Звук не должен быть единственным
сигналом успеха/reveal. `reduced-motion` не равен mute.

## 18. Error handling

Нужны четыре разных уровня, а не один общий toast:

1. **Bootstrap/chunk error:** React fallback с retry import/reload и возвратом в
   каталог.
2. **Asset error:** обязательный asset → fallback; необязательный → выключить
   эффект и продолжить. Ошибка логируется без персональных/секретных данных.
3. **API/read error:** сохранить последний server snapshot, показать
   reconnecting, exponential backoff с jitter и ручной retry. Никогда не
   подменять недоступные данные выдуманным тиражом.
4. **Purchase error:** разделять окончательную и неоднозначную ошибку согласно
   разделу 11; pending attempt не терять.

При sales cutoff выбранный, но не отправленный билет становится read-only и
переходит в waiting без покупки. При смене server format несовместимый client
snapshot сбрасывается и core UI строится из новых DTO; если формат не 3/16,
покупку блокировать и показать «Игра обновилась», а не пытаться угадать правила.

## 19. Какие существующие файлы нужно изменить

| Файл | Изменение |
|---|---|
| `archive/reference/legacy-web/frontend/web/package.json`, `package-lock.json` | добавить закреплённую совместимую версию `phaser`; не добавлять state library без необходимости |
| `archive/reference/legacy-web/frontend/web/src/App.tsx` | заменить `GrobGame` на lazy host, выделить grob entry/exit, отдельное обновление баланса без закрытия, удалить старые `GrobPicker`/`GrobLiveStage` после миграции |
| `archive/reference/legacy-web/frontend/web/src/api.ts` | типизировать полный PurchaseResponse, разрешить lifecycle `AbortSignal`, сохранить текущие credentials/CSRF |
| `archive/reference/legacy-web/frontend/web/src/types.ts` | синхронизировать недостающие поля `Lottery`, `LiveDraw`, purchase DTO; не создавать несовместимые копии |
| `archive/reference/legacy-web/frontend/web/src/styles.css` | оставить только host/fallback/a11y styles, удалить мёртвые grob HTML/CSS после parity |
| `archive/reference/legacy-web/frontend/web/src/App.test.tsx` | проверить lazy open/close, refresh и отсутствие закрытия после покупки |
| `frontend/Dockerfile` | убрать grob-зависимость web от miniapp assets, когда старые imports удалены; Mini App stage не менять |
| `archive/reference/legacy-web/docs/WEB_APP.md` | после реализации описать Phaser experience и быстрые покупки |
| `CHANGELOG.md`, `DEVLOG.md` | обновить при видимой реализации/release согласно правилам репозитория |

`backend`, `frontend/miniapp` и migrations для этой архитектуры менять не нужно.
Если реализация всё же потребует backend contract, сначала доказать это тестом/
ограничением и добавить соответствующие API/domain tests, не меняя математику.

## 20. Какие новые файлы нужно создать

Рекомендуемый минимальный набор:

- `archive/reference/legacy-web/frontend/web/src/grob/GrobExperienceHost.tsx`
- `archive/reference/legacy-web/frontend/web/src/grob/GrobExperienceHost.test.tsx`
- `archive/reference/legacy-web/frontend/web/src/grob/application/grob-reducer.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/application/grob-reducer.test.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/application/useGrobExperience.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/application/pending-purchase.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/application/pending-purchase.test.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/application/random-ticket.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/application/random-ticket.test.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/bridge/GrobBridge.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/bridge/contracts.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/phaser/createGrobGame.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/phaser/layout/GrobLayout.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/phaser/scenes/GrobBootScene.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/phaser/scenes/GrobPreloadScene.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/phaser/scenes/GrobPlayScene.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/phaser/scenes/GrobLiveScene.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/phaser/scenes/GrobOverlayScene.ts`
- `archive/reference/legacy-web/frontend/web/src/grob/phaser/audio/GrobAudioManager.ts` (только если есть audio)
- `archive/reference/legacy-web/frontend/web/src/grob/assets/core/*`
- `archive/reference/legacy-web/frontend/web/src/grob/assets/live/*`
- focused browser smoke test в принятом проектом e2e-каталоге; если его нет,
  сначала добавить минимальную Vite/Playwright smoke-инфраструктуру только для
  web, не смешивая с backend suite.

## 21. Предлагаемое дерево директорий

```text
frontend/web/src/
├─ App.tsx
├─ api.ts
├─ types.ts
└─ grob/
   ├─ GrobExperienceHost.tsx
   ├─ GrobExperienceHost.test.tsx
   ├─ application/
   │  ├─ grob-reducer.ts
   │  ├─ grob-reducer.test.ts
   │  ├─ useGrobExperience.ts
   │  ├─ pending-purchase.ts
   │  ├─ pending-purchase.test.ts
   │  ├─ random-ticket.ts
   │  └─ random-ticket.test.ts
   ├─ bridge/
   │  ├─ contracts.ts
   │  └─ GrobBridge.ts
   ├─ phaser/
   │  ├─ createGrobGame.ts
   │  ├─ layout/GrobLayout.ts
   │  ├─ scenes/
   │  │  ├─ GrobBootScene.ts
   │  │  ├─ GrobPreloadScene.ts
   │  │  ├─ GrobPlayScene.ts
   │  │  ├─ GrobLiveScene.ts
   │  │  └─ GrobOverlayScene.ts
   │  └─ audio/GrobAudioManager.ts
   └─ assets/
      ├─ core/
      │  ├─ pack.ts
      │  ├─ grob-core.webp
      │  └─ grob-core.json
      └─ live/
         ├─ pack.ts
         ├─ grob-live.webp
         └─ grob-live.json
```

Не создавать общий `game-engine` package: Phaser требуется только одной
лотерее. Если в будущем вторая независимая игра действительно переиспользует
bridge/layout, обобщение выполнить после появления второго подтверждённого use
case.

## 22. Пошаговый implementation plan для следующего агента

1. Зафиксировать baseline: `git status`, web lint/typecheck/test/build, снять
   скриншоты текущего catalog/grob/live и размеры build chunks.
2. Добавить Phaser в `archive/reference/legacy-web/frontend/web`, проверить Vite production build и создать
   lazy boundary без сцены. Убедиться, что catalog initial chunk не включает
   Phaser.
3. Дополнить DTO/API typings и optional abort signal, не меняя endpoint/CSRF.
4. Реализовать чистые `random-ticket`, pending storage и reducer; покрыть
   переходы всех состояний, x1/x5/x25, format/cutoff и stale response тестами.
5. Реализовать instance-scoped bridge с тестом subscribe/dispose и revision.
6. Создать host/bootstrap/cleanup. В тесте подменить Phaser factory и доказать:
   StrictMode не оставляет второй game, unmount вызывает destroy, listeners и
   requests отменяются.
7. Провести короткий art spike с placeholder primitives: layout всех
   breakpoints, 16 hit targets, ручной ticket, быстрые кнопки. Сначала доказать
   игровой interaction, затем подключать тяжёлый art.
8. Подготовить и оптимизировать core atlas. Реализовать Boot/Preload/Play/Overlay,
   reduced motion и keyboard focus. Никаких API calls из scenes.
9. Подключить ручной purchase flow: fresh preflight, persist-before-send,
   single-flight, окончательные/неоднозначные ошибки, успех и автоматический
   пустой билет без unmount.
10. Подключить quick x1/x5/x25 одним атомарным запросом и проверить, что x5 не
    превращается в `draw_count=5`.
11. Подключить grob-only live polling и LiveScene. Тестами с fake clock проверить
    waiting, поздний вход, каждый reveal, win/loss/spectator, background resume и
    reconnect.
12. Добавить live pack и optional audio только после профилирования core.
13. Добавить accessibility mirror/fallback и canvas/WebGL failure paths.
14. Перевести `App.tsx` на новый host, сохранить catalog/account/tickets. После
    успешного smoke удалить `GrobGame.tsx`, недостижимый `GrobPicker`, старый
    `GrobLiveStage` и их CSS/assets. Telegram Mini App не менять.
15. Выполнить focused checks: web lint, typecheck, tests, build и browser smoke на
    desktop/mobile, reduced motion, Canvas fallback, offline/retry и десять
    mount/unmount циклов. Проверить chunk/asset budgets и memory.
16. Перед release выполнить требуемый полный project suite согласно AGENTS.md,
    обновить `WEB_APP.md`, `CHANGELOG.md`, `DEVLOG.md`. Недоступные проверки явно
    задокументировать.
17. Сделать небольшой логический commit без `.env`. После успешного release —
    backup, deploy только затронутого gateway (backend не перестраивать, если он
    не менялся), затем production health и ручной `/web/` smoke. При небезопасном
    deploy остановиться и сообщить владельцу.

### Обязательные acceptance checks

- ручная покупка: три числа → один клик → один билет → новый пустой билет;
- quick x1/x5/x25 создают ровно 1/5/25 ticket IDs и один API request;
- double click/Enter не создают вторую покупку;
- reload после timeout предлагает тот же pending attempt;
- смена draw при uncertain attempt не покупает новый draw автоматически;
- cutoff блокирует отправку до визуальной анимации покупки;
- live никогда не показывает число раньше его `reveal_at`;
- late join и возврат вкладки сразу соответствуют server time;
- результат/выигрыш берётся из API, не рассчитывается сценой;
- выход и повторный вход не оставляют canvas, audio, poll или listener;
- login, каталог, другие игры и Telegram Mini App не изменены.

## 23. Риски

| Риск | Последствие | Митигация |
|---|---|---|
| Phaser увеличит initial bundle | медленный login/catalog | dynamic import и проверка Vite chunks |
| StrictMode создаст два game | canvas/listener/memory leak | ref-guard, factory test, симметричный cleanup |
| Canvas UI недоступен клавиатуре/screen reader | нарушение доступности | focus model + скрытый DOM mirror + aria-live |
| Client clock drift | ранний/поздний reveal и cutoff | server offset, re-sync каждый response/foreground |
| Poll responses придут не по порядку | возврат к старому draw | abort, sequence/revision и draw-number guard |
| Неоднозначная purchase при смене draw | билет попадёт не в ожидаемый тираж | persisted immutable attempt, stale block, ручная проверка; не retry в новый draw |
| x5 перепутают с `draw_count=5` | 25 билетов/неожиданная стоимость | отдельный quantity payload, contract tests |
| Client hardcode 3/16/6666 | рассинхронизация с admin/server | строить из Dashboard, format guard, server validation |
| Слишком тяжёлые фон/FX/audio | память, низкий FPS, долгий старт | budgets, atlases, lazy live, DPR/quality cap, particle pool |
| WebGL/context failure | пустой экран | Phaser.AUTO, Canvas fallback, context recovery, DOM fallback |
| Старый CSS/компоненты останутся | дублирование и регрессии | удалить после parity, `rg grob`, build/test |
| Импорт assets из Mini App | случайное изменение Telegram-клиента/сборки | собственные web packs, убрать cross-tree import |
| Phaser state начнёт жить отдельно от React/server | расхождение баланса/тиража | однонаправленные snapshots, API только в controller |
| Аудио autoplay | браузер блокирует/раздражает игрока | user gesture, mute control, optional pack |

## 24. НЕ ДЕЛАТЬ

- Не переписывать весь Casper.
- Не менять Telegram Mini App.
- Не переписывать backend без необходимости.
- Не менять существующую математику, расписание, settlement, ledger или формат
  «ГРОБ».
- Не создавать второй источник игровой логики на клиенте.
- Не рассчитывать выигрыш, валидность тиража или authoritative balance в Phaser.
- Не возвращаться к обычному HTML dashboard, арт слева / UI справа, карточкам и
  grid-панели как основной сцене.
- Не заменять Phaser CSS-имитацией.
- Не делать тяжёлую 3D-игру, Three.js/WebGL engine поверх Phaser или сложную
  физику без продуктовой необходимости.
- Не обращаться к API непосредственно из Phaser scenes.
- Не делать глобальный event bus на `window` и не хранить GameObjects в React.
- Не preload-ить live/audio assets при старте каталога.
- Не использовать `Math.random` для quick tickets и не регенерировать payload
  при retry.
- Не путать quick x5 билетов с `draw_count: 5` тиражей.
- Не показывать confirmation modal перед покупкой.
- Не закрывать игру после успешной покупки; сразу выдавать новый пустой билет.
- Не раскрывать номера по локальному таймеру раньше серверных `reveal_at`.
- Не оставлять реальные токены, cookie, CSRF или `.env` в логах/документации.
- Не усложнять решение отдельным package, XState, Redux, WebSocket или новым
  backend endpoint, пока существующие простые контракты решают задачу.

