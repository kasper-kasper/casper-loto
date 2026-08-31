# Telegram Mini App

Telegram Mini App is the primary player interface. The Telegram bot binds the
player, delivers durable notifications and opens this signed HTTPS client.

## Scope

Milestone 5 provides a mobile-first React/TypeScript/Vite client with:

- server-authoritative animated balance and independent lottery cards;
- Weekly 5/20 and Daily 4/15 number pickers with Web Crypto random pick;
- single-ticket purchase and multi-ticket cart checkout;
- duplicate combinations as independent cart tickets;
- active tickets, completed ticket history and recent results;
- polished mobile navigation, loading and result states with optional Telegram
  haptic feedback;
- a permanent server-synchronised **Эфир** screen for waiting, sequentially
  revealing the immutable result and showing the personal outcome;
- responsive layout from 320px with Telegram/iPhone safe-area support.

The v0.18.0 visual system uses layered navy surfaces, restrained blue and
burgundy depth, and gold only for jackpots, money, wins and primary actions.
Decorative lottery balls are intentionally not used. Functional number choices
are rounded tiles.

## Эфир

`GET /api/v1/miniapp/live` is an authenticated read-only projection. It returns
the server clock, the latest completed draw, the next scheduled draw and a
bounded personal summary. It never generates numbers and never starts or
settles a draw. The existing scheduler and cryptographically secure backend RNG
remain the only source of the immutable result.

The client derives the visual phase from the server-time offset and the official
UTC `scheduled_at`: waiting, short start, two-second sequential reveal and final
result. Opening late or returning from the background triggers a fresh sync and
resumes the correct phase without replaying a completed draw. Polling is active
only while the screen is open; no WebSocket or streaming infrastructure is used.

The screen uses a low-cost CSS grid and one blurred ambient glow. Number reveal
uses only opacity, blur and transform. Reduced-motion preferences, 320px layouts
and Telegram/iPhone safe areas are preserved.

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
