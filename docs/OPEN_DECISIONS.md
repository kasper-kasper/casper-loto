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
