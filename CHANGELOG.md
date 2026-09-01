# Changelog

All notable changes follow Keep a Changelog and Semantic Versioning principles.

## [1.5.0] - 2026-09-01

### Добавлено

- После покупки Mini App показывает понятное подтверждение с действиями «Купить ещё» и
  «Мои билеты».
- Главная Admin Panel получила общую сводку по билетам, тиражам, выигрышам, расходам и
  результату игроков за всё время.
- В статистике чисел появился выбор периода: все доступные, 10, 20, 50 или 100 последних
  тиражей выбранной лотереи.
- Аналитика билетов теперь показывает фактическую долю выигрышей, историческую сложность и
  долю возврата CAS отдельно по каждой лотерее.

### Изменено

- Admin Panel оформлена как закрытый оперативный штаб владельца с более крупной типографикой,
  спокойной агентской стилистикой и деликатными анимациями.
- Статистика выпавших чисел начинает новый аналитический период с 1 сентября 2026 года, не
  удаляя и не изменяя историю тиражей.
- Файл дальнейшего плана полностью актуализирован: выполненные этапы удалены, сохранены только
  реальные направления развития проекта.

### Исправлено

- После покупки игрок больше не переносится автоматически в раздел билетов и может сразу
  продолжить покупку в той же лотерее.

## [1.4.2] - 2026-09-01

### Изменено

- Главная снова открывается с ближайшего тиража, его джекпота, времени и кнопок действий.
- Компактная лента остальных лотерей расположена сразу под ближайшим тиражом и остаётся видимой
  на первом экране телефона.
- Удалены поясняющие подписи «Сегодня в Каспер», «Выберите лотерею» и
  «Нажмите, чтобы переключить».

### Исправлено

- Уменьшена избыточная высота сцены и внутренних отступов карточки ближайшего тиража без удаления
  игровой информации и действий.

## [1.4.1] - 2026-09-01

### Изменено

- Переключатель лотерей теперь расположен сразу под логотипом и виден без
  прокрутки при открытии Mini App.
- Логотип «Каспер» собран в единый компактный фирменный знак, где золотая
  буква «К» является частью слова.
- Иллюстрация в покупке стала компактной живой шапкой с названием поверх,
  поэтому поле выбора чисел начинается значительно выше.

### Исправлено

- Убран критический пустой отступ перед полем чисел на экранах ПЛЛ, ПСС, ХАН,
  Weekly и «3 СЕНТЯБРЯ».
- Игроку больше не требуется прокручивать отдельную большую фотографию перед
  началом выбора комбинации.

## [1.4.0] - 2026-09-01

### Добавлено

- ПЛЛ, ПСС, ХАН и Weekly получили самостоятельные кинематографичные заставки
  с раздельными планами, живым светом и атмосферными эффектами.
- Для ПСС создана новая тёмная природная сцена с северным лесом, озером,
  туманом и грозовым светом.
- Главная, выбор чисел и эфир используют единый визуальный мир каждой
  лотереи, сохраняя плавные переходы между состояниями.

### Изменено

- Главная перестроена вокруг крупной иллюстрированной сцены и компактной
  ленты расписания вместо набора одинаковых карточек.
- Экраны выбора чисел получили разные композиции: ночные координаты ПЛЛ,
  природную панель ПСС, монументальные знаки ХАН, клубный билет Weekly и
  осенние главы «3 СЕНТЯБРЯ».
- Разделы «Моё», корзина и эфир получили новую иерархию и оформление.

### Исправлено

- Убран зазор между верхней границей окна выбора и изображением лотереи.
- Старые стили общей сетки больше не нарушают расположение чисел ПЛЛ, ПСС,
  ХАН и Weekly.
- Иллюстрации больше не перекрывают название, время и сумму главного приза.

## [1.3.0] - 2026-09-01

### Добавлено

- Mini App получил собственный визуальный язык Design 2.0 с фирменным мотивом
  `2:22`, геометрическими линиями и обновлёнными иконками навигации.
- Эфир стал полноценной атмосферной сценой: фон и геометрия плавно оживают к
  началу тиража, сохраняя лёгкость и скорость интерфейса.
- Для лотереи «3 СЕНТЯБРЯ» добавлены отдельные календарные композиции на
  главной, в выборе чисел и в эфире.

### Изменено

- Главная, карточки тиражей, выбор чисел, билеты и нижняя навигация получили
  более выразительную иерархию, глубину и короткие микроанимации.
- Эфир «3 СЕНТЯБРЯ» теперь явно отображает правильный формат 3 из 33.

## [1.2.1] - 2026-09-01

### Исправлено

- Отдельная лотерея «3 СЕНТЯБРЯ» теперь начинает собственную нумерацию с
  тиража №1 и билета №1, а не продолжает номера других лотерей.

## [1.2.0] - 2026-09-01

### Добавлено

- В Mini App появилась новая ежедневная лотерея «3 СЕНТЯБРЯ»: 3 числа из 33,
  билет за 333 CAS и тиражи в 03:33 и 15:33 по Москве.
- Фиксированный главный приз 33 333 333 CAS делится между всеми билетами с
  результатом 3/3; выплаты за 1/3 и 2/3 составляют 333 и 3 333 CAS.
- Лотерея получила собственное бордово-терракотовое оформление с календарным
  мотивом и отдельным визуальным состоянием выбора чисел.

### Изменено

- Универсальные стратегии теперь поддерживают фиксированные выплаты и
  восстановление постоянного главного приза из отдельного резерва.
- Названия главного приза и подсказки новой лотереи доступны в общем файле
  редактируемых текстов Mini App.

## [1.1.0] - 2026-09-01

### Добавлено

- Универсальные стратегии правил и расписаний подготовили K-Loto к добавлению новых форматов без копирования сервисов покупки и расчёта.
- Открытый Mini App теперь предлагает безопасно загрузить готовое обновление и сохраняет текущую корзину при перезагрузке вкладки.
- Подготовлены проверяемая выгрузка резервной копии вне VPS и изолированный PostgreSQL smoke-тест на 5 000 билетов.

### Исправлено

- Восстановлена работа кнопки «Сохранить комбинацию»; сохранённое состояние теперь сразу видно игроку.
- Документация приведена к фактическим SSE-соединению и лимитам: до 1 000 билетов в одной покупке и до 5 000 билетов игрока на тираж по умолчанию.

## [1.0.2] - 2026-09-01

### Изменено

- Название «Каспер» в шапке Mini App оформлено как единый премиальный wordmark:
  золотой знак «К» соединён с продолжением на глубокой синей поверхности.
- Для маленьких экранов добавлены отдельные компактные размеры логотипа.

## [1.0.1] - 2026-09-01

### Исправлено

- Название в шапке Mini App теперь читается единым словом «Каспер»: дизайнерская
  «К» в золотом квадрате является первой буквой, а рядом отображается «аспер».

## [1.0.0] - 2026-09-01

### Добавлено

- В Admin Panel появилась общая и отдельная по каждой лотерее аналитика
  билетов, выигрышей, участников, продаж и выплат.
- Каждый раздел Admin Panel получил собственный адрес в браузере.

### Изменено

- После обновления страницы Admin Panel сохраняет открытый раздел вместо
  возврата на «Обзор».
- CHANGELOG продолжает официальную историю релизов по Semantic Versioning без
  изменения старых записей `0.x`; DEVLOG получил отдельную сквозную нумерацию.

## [0.23.1] - 2026-09-01

### Изменено

- Настройка Telegram-уведомлений в профиле сведена к одной понятной кнопке:
  «Включить уведомления» или «Отключить уведомления».
- Обновлены шапка, подписи главной страницы и заголовок раздела «Моё» в стиле
  Каспера; убраны лишние служебные формулировки.
- Карточки статистики стали крупнее и дополнены количеством активных билетов и
  процентом выигрышных билетов без новых серверных запросов.
- Файл пользовательских текстов разделён по экранам и дополнен инструкцией по
  самостоятельной публикации из VS Code одной командой.

### Исправлено

- Последовательное появление чисел в прямом эфире теперь начинается после
  фактической готовности результата и не пропускается при задержке scheduler.
- Новые и изменённые русские тексты вычитаны по орфографии и пунктуации.

## [0.23.0] - 2026-09-01

### Добавлено

- В профиле Mini App появилась добровольная проверка связи с Telegram-ботом:
  игрок сам запрашивает диагностическое сообщение после выдачи разрешения.
- Автоматический контроль зависших уведомлений и расчётов тиражей с
  оповещением владельца о проблеме планировщика.

### Изменено

- Персональное автоучастие владельца больше не показывается в публичном
  профиле игроков и остаётся закрытой функцией Admin/backend.
- Основные подписи Mini App собраны в одном понятном файле с инструкцией по
  безопасному редактированию.
- Telegram-бот упрощён до открытия Mini App и доставки разрешённых
  уведомлений; устаревший дублирующий игровой интерфейс удалён.
- Старые недоставимые уведомления о покупке корректно помечаются отменёнными и
  больше не занимают очередь повторной доставки.

### Надёжность

- Добавлены воспроизводимая нагрузочная проверка тысяч билетов, проверка
  фактического восстановления PostgreSQL из резервной копии и единый сценарий
  выпуска на VPS.
- Docker-контекст очищен от локальных файлов, а слои сборки лучше используют
  кэш без удаления DEVLOG и CHANGELOG из Admin Panel.

## [0.22.0] - 2026-09-01

### Добавлено

- Новый раздел Mini App «Моё»: личная статистика, активные и завершённые билеты,
  внутренний центр уведомлений и настройки сообщений Telegram.
- Внутренние уведомления о выигрышах и приглашения в ближайший открытый тираж.
- Управляемое владельцем автоучастие: пять случайных билетов игрока создаются
  сервером один раз для каждого открытого тиража.
- Управление автоучастием в карточке игрока Admin Panel с обязательной причиной
  и записью в аудит.

### Изменено

- Бот отправляет только результат тиража, в котором у игрока был билет, и
  напоминание после 24 часов без покупки — исключительно после разрешения
  пользователя в Telegram.
- Отдельное сообщение бота о каждой покупке отключено; успешная покупка сразу
  отражается в Mini App.
- Раздел «Билеты» объединён с личной статистикой и уведомлениями под вкладкой
  «Моё», не увеличивая нижнюю навигацию.

### Безопасность и надёжность

- Согласие и категории уведомлений хранятся отдельно для каждого игрока;
  повторная доставка защищена уникальными ключами событий.
- Автобилеты используют криптографически стойкий генератор, обычный сервис
  покупки, integer CAS, ledger и стабильный idempotency key на тираж.
- Содержимое внутреннего уведомления неизменяемо; отметить прочитанным можно
  только отдельным полем времени.

## [0.21.0] - 2026-09-01

### Добавлено

- Покупка одной комбинации на текущий и следующие четыре тиража с явным
  выбором, полной стоимостью до подтверждения и без автоматического продления.
- Серверная временная шкала эфира и SSE-обновления с восстановлением правильного
  этапа после повторного открытия Mini App.
- Избранные комбинации в Mini App, фильтры истории по лотерее и выигрышам и
  показатель общей суммы выплат за текущий месяц.
- Статусы продаж: открыты, скоро закроются, закрыты, идёт розыгрыш и завершён.
- Оперативный пульт владельца: ближайшие тиражи, участники, продажи, состояние
  планировщика, зависшие расчёты и очередь уведомлений.

### Изменено

- Корзина до 1000 комбинаций одной лотереи теперь оформляется одной
  идемпотентной серверной операцией вместо пакетов по 100.
- В админ-панели доступны поиск игроков и управление cutoff и лимитами;
  изменения журналируются и не затрагивают завершённые тиражи.

### Безопасность и надёжность

- Добавлены серверные ограничения: до 1000 комбинаций за покупку, до 5000
  билетов игрока в одном тираже и ограничение частоты попыток покупки.
- Состояние планировщика сохраняется в PostgreSQL; все списания мультитиража и
  движения фондов по-прежнему проходят только через неизменяемый ledger.

## [0.20.0] - 2026-09-01

### Добавлено

- Цифровые повторы последних двух завершённых тиражей каждой лотереи без
  хранения видео и повторного выбора результата.
- Старые общие Daily-тиражи в архиве сохраняют публичное имя и стиль своего
  временного слота: ПЛЛ, ПСС или ХАН.
- Индивидуальная визуальная атмосфера ПЛЛ, ПСС, ХАН и Weekly при общей понятной
  механике покупки.
- Предварительный вид выбранной комбинации и группировка билетов и корзины по
  лотереям и тиражам.

### Изменено

- Главная Mini App перестроена вокруг одного выбранного тиража и компактной
  строки расписания вместо набора крупных карточек.
- Прямой эфир и повтор получили разные, явно подписанные визуальные состояния.
- Нижняя навигация получила собственный набор иконок K-Loto и более заметное,
  но спокойное активное состояние.
- Админ-панель приведена к общей сине-бордово-золотой стилистике K-Loto без
  анимаций и без изменения рабочих сценариев.

### Безопасность

- Повторы используют только сохранённые неизменяемые результаты; RNG,
  settlement, ledger и расписание не изменены.

## [0.19.0] - 2026-08-31

### Добавлено

- Быстрые действия на главной: активные билеты, случайная комбинация и повтор
  последней комбинации.
- Крупная корзина до 1000 билетов с прогрессом покупки и безопасной обработкой
  пакетами по 100 билетов.
- Живое ожидание эфира: линия сигнала, подготовка ячеек результата и отдельное
  визуальное состояние последней минуты.
- Количество личных билетов и точное время завершения продаж в карточках
  тиражей.

### Изменено

- Главная страница получила выразительный блок ближайшего тиража и более
  компактные карточки остальных лотерей.
- Эфир стал визуально активным до начала розыгрыша, сохранив спокойную
  премиальную стилистику без шаров, видео и тяжёлых эффектов.

### Исправлено

- Устранено ложное сообщение о закрытых продажах из-за устаревшего состояния
  Mini App: расписание теперь обновляется перед выбором чисел, каждые 15 секунд
  и после возврата приложения из фона.
- Непроданные билеты больше не исчезают при ошибке внутри крупной покупки.

## [0.18.0] - 2026-08-31

### Добавлено

- Постоянная вкладка «Эфир» в Telegram Mini App с ожиданием ближайшего тиража,
  серверным обратным отсчётом и последовательным появлением выпавших чисел.
- Персональный итог эфира: выигрыш, совпадения, спокойное сообщение о проигрыше
  или отсутствии участия, а также переход к следующему тиражу.
- Быстрый переход в эфир с главной страницы перед началом розыгрыша.

### Изменено

- Нижняя навигация расширена до четырёх компактных разделов без изменения
  покупки билетов и игровой математики.
- При возврате в Mini App эфир повторно синхронизируется с сервером и сразу
  продолжает с актуального этапа.

### Безопасность

- Эфир только читает сохранённый неизменяемый результат; RNG, scheduler и
  settlement не изменены.

## [0.17.0] - 2026-08-31

### Добавлено

- Обновлённая дизайн-система Telegram Mini App в премиальной
  сине-бордово-золотой стилистике.
- Компактный блок ближайшего тиража, живой таймер и информативные карточки
  лотерей.
- Плавное изменение баланса, состояния покупки, skeleton-загрузка и безопасная
  тактильная отдача Telegram.

### Изменено

- Полностью переработаны главный экран, выбор чисел, карточки билетов, корзина
  и нижняя навигация без изменения игровой логики.
- Выигрышные и проигрышные билеты теперь имеют разный визуальный приоритет;
  нулевой выигрыш и нулевой джекпот больше не выделяются золотым.

### Исправлено

- Удалены технические сообщения из пустой корзины.
- Исправлена генерация локального dev-секрета в Windows PowerShell.

## [0.16.1] - 2026-08-31

### Fixed

- Admin project journals are located correctly inside the installed production
  backend container.

## [0.16.0] - 2026-08-31

### Added

- A protected **Development** area in Web Admin with separate CHANGELOG and
  DEVLOG tabs.
- The complete existing release history is now available from the Admin Panel.

### Changed

- Project release journals are delivered through the authenticated Admin site.

### Removed

- Telegram DevLog/ChangeLog delivery and its token/chat configuration tooling.

## [0.15.0] - 2026-08-31

### Changed

- Telegram bot is now a notification and Mini App entry channel.
- `/start` immediately offers the Mini App instead of the legacy gameplay menu.
- A persistent **Играть в K-Loto** button is shown beside the message field.
- Purchase and result notifications open the Mini App directly.
- The public bot command list is reduced to the single `/start` entry point.

## [0.14.0] - 2026-08-31

### Added

- Independent ПЛЛ-лото, ПСС-Лото and ХАН-Лото with separate draws, ticket
  numbering and funds at 02:22, 12:00 and 18:00 Moscow time.
- One-time automatic 100,000,000,000 CAS Telegram welcome allocation.
- Premium blue/red/gold Telegram Mini App for all four lotteries.
- Empty-draw broadcasts with current jackpot and a direct purchase button.
- Telegram favourites, next-draw countdowns, ticket pagination and random
  batches of 5, 10, 25 or 50 tickets.

### Changed

- ПСС and ХАН start with independent 24,000,000 CAS jackpots; ПЛЛ safely
  inherits the shared Daily funds after already purchased tickets settle.
- The Telegram bot and Mini App are now the only player interfaces.
- Web Admin remains a separate permanent HTTPS site and is fully localized.

### Removed

- Ordinary username/password player Web application and its runtime API.

### Fixed

- Daily selection now remains bound to the exact chosen lottery and draw.
- Admin saves lottery price, base jackpot and reserve with clear feedback.

## [0.13.1] - 2026-08-15

### Changed

- Weekly and Daily current jackpots are always visible in the player Web header.
- Jackpot and balance information refresh automatically every 15 seconds, when
  the browser regains focus and by an explicit refresh button.
- Web purchase failures now return clear Russian explanations.

### Fixed

- Fixed Web purchases failing after authentication because the authentication
  query and protected financial operation shared one SQLAlchemy transaction.

## [0.13.0] - 2026-08-15

### Added

- One-click player Web login directly from each Telegram account.
- `/web` bot command and a permanent Web button in the main bot menu.
- Five-minute one-time login tokens with migration
  `0005_telegram_web_login`.

### Changed

- Manual Web username/password provisioning is now an optional fallback instead
  of a required setup step.
- The player Web login page now points users to the simpler Telegram flow.

### Security

- Only SHA-256 token hashes are stored in PostgreSQL.
- Raw one-time tokens use URL fragments, do not enter server request URLs and
  are atomically invalidated after the first successful exchange.

## [0.12.0] - 2026-08-15

### Added

- Permanent HTTPS player Web and Admin sites on the owner-authorized VPS.
- Always-on API, scheduler, recovery worker, Telegram bot and PostgreSQL stack.
- Idempotent production bootstrap for Weekly/Daily lotteries and their next draws.
- Daily compressed PostgreSQL backups with 14-day retention.
- Production operation and first-player setup documentation.

### Changed

- Database check-constraint names now match SQLAlchemy metadata through migration
  `0004_constraint_names`.
- PostgreSQL trigger creation in the initial migrations is compatible with the
  asyncpg prepared-statement execution model.

### Security

- PostgreSQL remains private to the Docker network; HTTPS certificates renew
  automatically through Caddy.
- Production credentials exist only in the ignored owner `.env` and the
  permission-restricted VPS environment file.
- Existing VPS VPN services and their ports remain untouched.

## [0.11.0] - 2026-08-15

### Added

- Fully playable Daily Lottery 4 of 15 in Telegram and player Web.
- Daily draws at 02:22 and 18:00 Europe/Moscow with a two-minute cutoff.
- Daily 40/60 jackpot/distribution contributions and approved prize tiers.
- Daily settlement, reserve fallback, carryovers, jackpot reset and recovery.
- Audited Web-login provisioning for players from the Admin Panel.

### Changed

- Scheduler recovery now settles overdue Weekly and Daily draws in one
  chronological sequence.
- Player Web and Admin clients are versioned with the Daily release.

### Security

- Daily purchases and settlement use row locks, immutable ledger records,
  idempotency keys and durable notification events.
- Guaranteed Daily prizes never consume jackpot; insufficient reserve aborts
  settlement atomically.

## [0.10.0] - 2026-08-15

### Added

- Ordinary browser player application with Weekly 5/20 gameplay.
- Password login, current CAS balance, active tickets and settled history.
- Completed draw result archive and 1-to-20-ticket purchase interface.
- One-to-one Web accounts for existing players and migration
  `0003_web_accounts`.
- Local account configurator and player Web start command.

### Changed

- Standard project checks now validate and build the frozen Mini App, Admin
  Panel and ordinary player Web client.
- The permanent deployment plan now has a defined player Web authentication
  flow.

### Security

- Player passwords use Argon2 hashes and are never returned to the browser.
- Signed expiring HttpOnly sessions use an independent secret, SameSite/Secure
  cookie controls and per-session CSRF protection.
- Weekly purchases remain server-authoritative, atomic and idempotent through
  the existing application service and immutable ledger.

## [0.9.0] - 2026-08-15

### Added

- Complete Telegram bot gameplay menu with balance, lotteries and rules.
- Weekly 5/20 inline number picker, secure random pick and multi-ticket cart.
- Atomic Telegram checkout with duplicate-combination support and idempotency.
- Active tickets, settled history, recent draw archive and player statistics.
- Configurable Telegram purchase batch limit.
- Permanent deployment plan for always-on API, bot, user Web and Admin site.

### Changed

- Telegram bot is now the primary player interface; the Mini App remains frozen.
- Admin production target is an ordinary continuously available HTTPS website,
  while local start commands remain development-only.

### Security

- Telegram prices, draw assignment, balances and payouts remain server-authoritative.
- Repeated checkout callbacks use one stable idempotency identity and cannot
  create a second financial operation.

## [0.8.0] - 2026-08-15

### Added

- Separate authenticated Web Admin Panel with operational dashboard.
- Player financial overview and idempotent balance adjustments through ledger.
- Lottery price/base-jackpot configuration and reserve ledger adjustments.
- Filterable immutable CAS ledger, administrator audit and read-only draw archive.
- Number appearance statistics derived from completed draw history.
- Argon2 administrator credential setup, signed HttpOnly sessions and CSRF protection.

### Changed

- Telegram Mini App is preserved but frozen; active player UI roadmap is now the
  full Telegram bot followed by a simple user Web version.
- Standard frontend checks now cover both the preserved Mini App and Admin Panel.

### Security

- Administrator mutations require an authenticated session, CSRF token,
  mandatory reason and backend ledger/audit use cases.
- Completed draws have no administrator mutation endpoint.

## [0.7.0] - 2026-08-15

### Added

- One-command local browser development mode without Telegram authentication.
- Idempotent local test player, playable lottery fixtures and ledgered test CAS.
- Development-only balance refill through the immutable ledger.
- Loopback-only signed HttpOnly development sessions.
- Separate Telegram tunnel frontend mode with a free Cloudflare Quick Tunnel
  helper and no browser authentication bypass.
- Beginner-focused local PostgreSQL, browser and Telegram tunnel guide.

## [0.6.0] - 2026-08-15

### Added

- Telegram Mini App dashboard with balance, Weekly/Daily cards, jackpots and
  countdowns.
- Weekly 5/20 number picker, random selection and single-ticket purchase.
- Multi-ticket cart checkout with configurable expiring persistence.
- Active tickets, completed history and recent results.
- Server-side Telegram `initData` authentication for every Mini App request.
- Configurable Mini App launch button in the Telegram bot.

### Fixed

- Purchases after the Weekly cutoff now atomically prepare and use the next
  numbered draw without waiting for the current draw settlement.

## [0.5.0] - 2026-08-14

### Added

- Telegram player bot with `/start` and idempotent user/balance binding.
- Purchase confirmations for single and multi-ticket orders.
- Per-user Weekly draw-result notifications, including losing tickets.
- Durable notification outbox with retry, recovery and duplicate protection.
- Separate bot runtime for local and Docker Compose operation.

## [0.4.0] - 2026-08-14

### Added

- Weekly schedule at Sunday 20:00 Europe/Moscow with a 19:55 sales cutoff.
- Automatic preparation and independent numbering of the next draw.
- Startup and periodic reconciliation of missed Weekly draws.
- Chronological recovery of several missed draws after downtime.
- Confirmed Daily schedule slots at 02:22 and 18:00 Europe/Moscow.
- APScheduler runtime integrated with backend application lifespan.

## [0.3.0] - 2026-08-14

### Added

- Atomic single- and multi-ticket purchases for Weekly 5/20.
- Server-authoritative draw selection after a sales cutoff.
- Complete Weekly payout calculation for categories 0/5 through 5/5.
- Jackpot and distribution contributions, carryovers and jackpot reset.
- Reserve fallback for guaranteed 2/5 and 3/5 prizes.
- Cryptographically secure official draw generation.
- Idempotent purchase and settlement processing, including empty draws.

## [0.2.0] - 2026-08-14

### Added

- Secret-safe Telegram DevLog chat discovery and notification scripts.
- Complete initial domain schema for users, lotteries, draws, tickets, CAS
  accounts, immutable ledger and administrator audit history.
- Database-enforced immutable completed draws, settled tickets and ledger rows.
- Independent per-lottery draw and ticket numbering foundations.

## [0.1.0] - 2026-08-14

### Added

- Initial K-Loto project foundation.
- FastAPI service with application/database health reporting.
- PostgreSQL, SQLAlchemy and Alembic configuration skeleton.
- Docker Compose development stack.
- Test, lint, format and type-check configuration.
- Architecture, security and unresolved-decision documentation.
