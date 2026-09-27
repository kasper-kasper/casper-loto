# Telegram Mini App

React, TypeScript and Vite client for Casper Loto. It authenticates every API request
with Telegram `initData`; balance, price, draw assignment and payout remain
server-authoritative.

```powershell
npm install
npm run dev:browser
```

Vite proxies `/api` to `http://localhost:8000`. Open the production build only
through the Telegram bot menu button so signed `initData` is available.

Browser mode first requests a loopback-only HttpOnly development session. For a
temporary Telegram HTTPS tunnel use `npm run dev:telegram`; that mode never asks
for or accepts the browser bypass.

`VITE_CART_TTL_SECONDS` controls local cart persistence. Until the owner resolves
the exact TTL, leave it blank; the cart then lasts only for the current open
Mini App session.

The first screen uses small derivatives of the approved brand artwork in
`public/brand/`. Keep the matching paths in `index.html` and `src/brand.ts`
in sync: the HTML preload, pre-React shell and React header should request
the same image. If the artwork changes, export a new sized derivative and
bump its filename version instead of replacing the approved master PNG.
