# Open decisions

| ID | Topic | Status | Decision |
|---|---|---|---|
| OD-001 | Daily lineup | Resolved 2026-09-02 | PLL 02:22/13:45, PSS 12:00/20:30 and KHAN 09:00/18:00 are independent entities. |
| OD-002 | Daily numbering | Resolved 2026-08-31 | Each entity starts at the current production Daily counters and advances independently. |
| OD-003 | Daily price | Resolved 2026-08-31 | Each starts with the current production Daily ticket price; Admin may configure later. |
| OD-004 | Daily payout | Resolved 2026-08-15 | 0/1 matches pay 0, 2 pays 50%, 3 pays 300%, 4 splits jackpot; 40/60 funding. |
| OD-005 | Daily jackpot | Resolved 2026-08-31 | PSS/KHAN start at 24m CAS; PLL preserves shared Daily funds. |
| OD-006 | Interfaces | Resolved 2026-08-31 | Telegram bot + Mini App for players, separate Web Admin; ordinary player Web removed. |
| OD-007 | Welcome grant | Resolved 2026-08-31 | Temporary automatic target grant is 100bn CAS once per Telegram identity through ledger. |
| OD-008 | Cart TTL | Open | Persistence stays disabled until the owner chooses a duration; session cart works. |
| OD-009 | Multi-draw purchase | Resolved 2026-09-01 | The player explicitly chooses 1 or 5 draws. All tickets and the full integer-CAS price are created and charged atomically up front; there is no renewal or later hidden debit. Paid contributions enter the lottery-wide funds at purchase time. |
| OD-010 | Player notifications | Resolved 2026-09-01 | Telegram is opt-in and sends only results for draws where the player owned a ticket plus one inactivity reminder after 24 hours without a purchase. Mini App stores wins and draw invitations in its own inbox. |
| OD-011 | Owner auto-play | Resolved 2026-09-01 | Telegram player 1201541335 receives five cryptographically random tickets once for every open draw. Purchases use the regular ledgered service and are controlled through audited Admin settings. |
| OD-012 | CAS purpose and audience | Resolved 2026-09-01 | CAS is permanently virtual and cannot be purchased, sold, withdrawn or exchanged for money or property. K-Loto is a private entertainment project for the owner and up to 50 friends, without public or commercial operation. |
| OD-013 | «3 СЕНТЯБРЯ» funding | Resolved 2026-09-01 | Tickets cost 333 CAS. One match pays 333, two pay 3,333, and 3/3 shares the 33,333,333 CAS main prize. Since 1.7.0 the unified funding rule in OD-015 applies. |
| OD-014 | «ГРОБ» rules | Resolved 2026-09-01 | Daily 3/16 at 06:06 and 23:06 Moscow, price 6,666 CAS, cutoff 2 minutes. One match pays 666, two pay 6,666, and 3/3 shares the 6,666,666 CAS base jackpot. Since 1.7.0 the unified funding rule in OD-015 applies. |
| OD-015 | Единая финансовая схема | Resolved 2026-09-04 | 100% цены нового билета поступает в джекпот его лотереи. Обычные выигрыши и восстановление базового джекпота оплачивает единый Фонд Каспера. Старые distribution/reserve сохранены только как финансовая история. Для Kasper Grand обычные категории рассчитываются как 20%/10%/8%/4%/2% накопительной части джекпота для 5+1/5+0/4+2/4+1/3+2 соответственно; полный 5+2 получает весь джекпот. |
| OD-016 | Fast | Resolved 2026-09-04 | FLASH (:00/:20/:40) и SHADOW (:10/:30/:50) — отдельные 3/15 лотереи по 888 CAS с cutoff 1 минута. 1/3 платит 88 CAS, 2/3 — 888 CAS, 3/3 делит собственный jackpot; базовый jackpot 888,888 CAS. Fast не входит в обычный эфир и приглашения, но показывает собственный короткий эфир внутри раздела Fast: за 20 секунд до старта, последовательная выдача чисел и 12 секунд результата. Результат сохраняется в Mini App; владельцу включены пять auto-play билетов и личный Telegram-результат на каждый Fast-тираж. |
| OD-017 | Kasper Grand | Resolved 2026-09-04 | Сущность `weekly` переходит с 5/20 на два независимых поля 5/35 + 2/5 без сброса нумерации. Старые завершённые тиражи остаются историей, активные старые билеты получают полный ledger-возврат, следующий тираж использует новый формат. |
