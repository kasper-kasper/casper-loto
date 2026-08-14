# Open decisions

Unresolved requirements are kept here instead of being guessed in code.

| ID | Decision | Status | Notes |
|---|---|---|---|
| OD-001 | Second Daily Lottery draw time | Resolved 2026-08-14 | The confirmed second slot is 18:00 Europe/Moscow. |
| OD-002 | Weekly ticket price | Open | Must be configurable in Admin. |
| OD-003 | Daily ticket price | Open | Must be configurable in Admin. |
| OD-004 | Weekly base jackpot | Open | Must be configured by the owner. |
| OD-005 | Daily base jackpot | Open | Must be configured by the owner. |
| OD-006 | Daily Lottery payout model | Open | Do not copy Weekly economics. |
| OD-007 | Cart TTL | Open | Must be short and configurable. Mini App persistence remains disabled until a value is supplied; the in-memory cart still works for the open session. |
| OD-008 | Final visual design | Open | Current visual references are directional only. |
| OD-009 | Reserve scope | Resolved 2026-08-14 | Per-lottery reserves, matching the Milestone 1 requirement. |
| OD-010 | Integer payout remainder allocation | Resolved 2026-08-14 | Allocate one extra CAS by ascending public ticket number until exhausted. |
| OD-011 | Behavior when reserve cannot cover guaranteed payouts | Resolved 2026-08-14 | Abort atomically and retry after reserve funding; never use jackpot or mint CAS. |
| OD-012 | Sales cutoff for Daily schedule slots | Open | Weekly cutoff is known; Daily cutoff is not specified. |

When the owner resolves an item, record the decision in the relevant
specification/configuration and mark the row `Resolved` with a date.
