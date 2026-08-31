# Telegram Mini App

Telegram Mini App is the primary player interface. The Telegram bot binds the
player, delivers durable notifications and opens this signed HTTPS client.

## Scope

Milestone 5 provides a mobile-first React/TypeScript/Vite client with:

- server-authoritative animated balance and a single focused lottery stage;
- Weekly 5/20 and Daily 4/15 number pickers with Web Crypto random pick;
- single-ticket purchase and multi-ticket cart checkout;
- duplicate combinations as independent cart tickets;
- active tickets, completed ticket history and recent results;
- polished mobile navigation, loading and result states with optional Telegram
  haptic feedback;
- a permanent server-synchronised **Эфир** screen for waiting, sequentially
  revealing the immutable result and showing the personal outcome;
- a digital replay archive with the latest two completed draws of every
  lottery, reconstructed from immutable draw facts without video storage;
- fresh sales-state checks before every number picker, background dashboard
  refresh and explicit cutoff time presentation;
- a cart of up to 1,000 tickets with idempotent 100-ticket server batches,
  visible progress and preservation of unpurchased combinations after failure;
- responsive layout from 320px with Telegram/iPhone safe-area support.

The v0.20.0 visual system uses layered navy surfaces, restrained blue and
burgundy depth, and gold only for jackpots, money, wins and primary actions.
The home screen has one selected lottery stage and a compact schedule switcher
instead of a wall of product cards. PLL, PSS, KHAN and Weekly retain the same
interaction model but have distinct night-violet, blue, burgundy and gold
accents. Decorative lottery balls are intentionally not used. Functional
number choices are rounded tiles.

## Эфир

`GET /api/v1/miniapp/live` is an authenticated read-only projection. It returns
the server clock, the latest completed draw, the next scheduled draw, the two
most recent completed draws per lottery and bounded personal summaries. It
never generates numbers and never starts or settles a draw. The existing
scheduler and cryptographically secure backend RNG remain the only source of
the immutable result.

The client derives the visual phase from the server-time offset and the official
UTC `scheduled_at`: waiting, short start, two-second sequential reveal and final
result. Opening late or returning from the background triggers a fresh sync and
resumes the correct phase without replaying a completed draw. Polling is active
only while the screen is open; no WebSocket or streaming infrastructure is used.

The screen uses a low-cost CSS grid and one blurred ambient glow. Number reveal
uses only opacity, blur and transform. Reduced-motion preferences, 320px layouts
and Telegram/iPhone safe areas are preserved.

The waiting state remains honest but visually active: a low-cost signal line,
result placeholders, a dedicated final-minute transition and server-synced
progress lead into the existing sequential reveal. No fake number or outcome is
ever displayed.

A replay is clearly marked as `ПОВТОР ТИРАЖА`, uses a calmer accent treatment
than the live state and animates the original stored sequence on the client.
There are no recording files, codecs or additional outcome generation. A replay
can be restarted or closed without affecting the live server timeline.

## Purchase limits and recovery

The application service rejects a purchase containing more than 100 tickets,
so the limit also applies when the HTTP API is bypassed. The Mini App can hold
up to 1,000 tickets and checks out grouped 100-ticket batches. Each batch owns a
stable idempotency key reused for one safe transient retry. Successfully bought
batches disappear from the cart immediately; any unprocessed tickets remain if
a later batch fails.

## Authentication and API

Every `/api/v1/miniapp/*` request carries `X-Telegram-Init-Data`. The backend
recomputes Telegram's HMAC, compares it in constant time, validates `auth_date`
and binds the signed Telegram user. Changed, expired, future-dated or malformed
payloads are rejected before database access.

The frontend never submits or calculates a ticket price, balance, draw ID,
jackpot contribution or payout. Weekly checkout calls the existing transactional
purchase service. When the previous draw has reached cutoff, that service creates
and assigns the next numbered Weekly draw while holding the lottery row lock.

## Cart TTL

`VITE_CART_TTL_SECONDS` enables expiring local persistence. The exact business
TTL is still OD-007 and has no guessed default. When unset, the cart works only
in memory for the current Mini App session. Expired or malformed stored carts
are discarded.

## Local checks

```powershell
Set-Location frontend/miniapp
npm run typecheck
npm run lint
npm test
npm run build
```

A deployed HTTPS URL is configured as `MINIAPP_URL`; `/start` and the persistent
Telegram menu button open the Mini App.
