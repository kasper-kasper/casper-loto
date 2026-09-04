# Telegram Mini App

Telegram Mini App is the primary player interface. The Telegram bot binds the
player, delivers durable notifications and opens this signed HTTPS client.

## Scope

Milestone 5 provides a mobile-first React/TypeScript/Vite client with:

- server-authoritative animated balance and a single focused lottery stage;
- Weekly 5/20, Daily 4/15 and «3 СЕНТЯБРЯ» 3/33 number pickers with Web Crypto random pick;
- single-ticket purchase and multi-ticket cart checkout;
- duplicate combinations as independent cart tickets;
- a «Моё» cabinet with player statistics, active tickets, completed ticket
  history, notification preferences and a persistent in-app inbox;
- polished mobile navigation, loading and result states with optional Telegram
  haptic feedback;
- a permanent server-synchronised **Эфир** screen for waiting, sequentially
  revealing the immutable result and showing the personal outcome;
- a digital replay archive with the latest two completed draws of every
  lottery, reconstructed from immutable draw facts without video storage;
- fresh sales-state checks before every number picker, background dashboard
  refresh and explicit cutoff time presentation;
- a cart of up to 1,000 tickets submitted as one idempotent server operation;
- responsive layout from 320px with Telegram/iPhone safe-area support.

The v0.20.0 visual system uses layered navy surfaces, restrained blue and
burgundy depth, and gold only for jackpots, money, wins and primary actions.
The home screen has one selected lottery stage and a compact schedule switcher
instead of a wall of product cards. PLL, PSS, KHAN and Weekly retain the same
interaction model but have distinct night-violet, blue, burgundy and gold
accents. Decorative lottery balls are intentionally not used. Functional
number choices are rounded tiles.

«3 СЕНТЯБРЯ» keeps the shared navigation and purchase flow but adds a restrained
burgundy, plum and terracotta theme. Its selected stage uses a subtle 03/09
calendar mark, while the 33-number picker resembles a paper date grid with a
soft marker-style selection. It adds no image, canvas or animation dependency.

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
resumes the correct phase without replaying a completed draw. The authenticated
SSE connection is active only while the relevant screen is open; WebSocket is
not required.

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

The application service and Mini App both cap one purchase at 1,000 tickets;
the default per-player/per-draw cap is 5,000. Each lottery group is submitted as
one server transaction with a stable idempotency key. The UI may show progress,
but it does not send thousands of individual requests.

The live feed uses authenticated SSE. Snapshots follow the server timeline;
reconnecting or reopening never restarts the reveal locally.

Fast uses the same read-only feed with `scope=fast`, but renders it directly in
the FLASH or SHADOW card. The card changes 20 seconds before the draw, reveals
the three immutable result numbers in sequence, holds the final result for 12
seconds and then returns automatically. The SSE connection exists only while
the Fast section is open.

## Authentication and API

Every `/api/v1/miniapp/*` request carries `X-Telegram-Init-Data`. The backend
recomputes Telegram's HMAC, compares it in constant time, validates `auth_date`
and binds the signed Telegram user. Changed, expired, future-dated or malformed
payloads are rejected before database access.

The frontend never submits or calculates a ticket price, balance, draw ID,
jackpot contribution or payout. Weekly checkout calls the existing transactional
purchase service. When the previous draw has reached cutoff, that service creates
and assigns the next numbered Weekly draw while holding the lottery row lock.

## Личный кабинет и уведомления

The bottom navigation item «Моё» combines overview, tickets and notifications.
The server derives all statistics from tickets and the immutable ledger. Wins
and draw invitations are stored in an inbox; opening the notification tab marks
only the read timestamp and never edits event content.

Telegram messages are disabled until the native `requestWriteAccess` prompt is
accepted. The settings screen controls draw-result and 24-hour inactivity
categories separately. A purchase itself is confirmed by the Mini App and no
longer creates a duplicate bot message.

## Cart TTL

The current tab stores its cart in `sessionStorage`, so a safe reload does not
lose selected combinations. `VITE_CART_TTL_SECONDS` optionally enables
persistence across Mini App sessions in `localStorage`. Expired or malformed
stored carts are discarded. A running client compares its bundled version with
the server and offers an explicit reload after release.

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
