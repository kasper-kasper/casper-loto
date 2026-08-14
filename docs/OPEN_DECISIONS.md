# Open decisions

Unresolved requirements are kept here instead of being guessed in code.

| ID | Decision | Status | Notes |
|---|---|---|---|
| OD-001 | Second Daily Lottery draw time | Open | Keep the second slot disabled/null. |
| OD-002 | Weekly ticket price | Open | Must be configurable in Admin. |
| OD-003 | Daily ticket price | Open | Must be configurable in Admin. |
| OD-004 | Weekly base jackpot | Open | Must be configured by the owner. |
| OD-005 | Daily base jackpot | Open | Must be configured by the owner. |
| OD-006 | Daily Lottery payout model | Open | Do not copy Weekly economics. |
| OD-007 | Cart TTL | Open | Must be short and configurable. |
| OD-008 | Final visual design | Open | Current visual references are directional only. |
| OD-009 | Reserve scope | Open | Choose system-wide or per-lottery reserve. |
| OD-010 | Integer payout remainder allocation | Open | Needed for equal splits in whole CAS. |
| OD-011 | Behavior when reserve cannot cover guaranteed payouts | Open | Must not be invented. |
| OD-012 | Sales cutoff for Daily schedule slots | Open | Weekly cutoff is known; Daily cutoff is not specified. |

When the owner resolves an item, record the decision in the relevant
specification/configuration and mark the row `Resolved` with a date.
