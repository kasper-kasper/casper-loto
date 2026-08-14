# Telegram Mini App

## Scope

Milestone 5 provides a mobile-first React/TypeScript/Vite client with:

- server-authoritative balance and lottery cards;
- Weekly 5/20 number picker and Web Crypto random pick;
- single-ticket purchase and multi-ticket cart checkout;
- duplicate combinations as independent cart tickets;
- active tickets, completed ticket history and recent results;
- read-only Daily card until Daily economics are approved.

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

A deployed HTTPS URL can be configured as `MINIAPP_URL`; `/start` then displays
the Telegram Web App launch button. Deployment itself remains Milestone 8.
