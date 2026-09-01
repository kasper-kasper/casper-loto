# Open decisions

| ID | Topic | Status | Decision |
|---|---|---|---|
| OD-001 | Daily lineup | Resolved 2026-08-31 | PLL 02:22, PSS 12:00 and KHAN 18:00 are independent entities. |
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
| OD-013 | «3 СЕНТЯБРЯ» funding | Resolved 2026-09-01 | Tickets cost 333 CAS and fund distribution. Fixed 1/3 and 2/3 payouts use distribution then reserve. A fixed 33,333,333 CAS main prize is shared by 3/3 tickets and refilled from a separate 1bn CAS reserve after a win. |
| OD-014 | «ГРОБ» rules | Resolved 2026-09-01 | Daily 3/16 at 06:06 and 23:06 Moscow, price 6,666 CAS, cutoff 2 minutes. One match pays 666, two pay 6,666 from distribution then reserve, and 3/3 shares the jackpot. Each ticket contributes 2,666 CAS to jackpot and 4,000 CAS to distribution; base jackpot is 6,666,666 CAS. |
| OD-015 | Единая финансовая схема | Resolved 2026-09-01 | Начиная с релиза 1.7.0, 100% цены нового билета поступает в джекпот его лотереи. Обычные выигрыши и восстановление базового джекпота оплачивает единый Фонд Каспера. Старые distribution/reserve сохранены только как финансовая история. Weekly 4/5 платит фиксированные 50,000 CAS. |
