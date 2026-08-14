# Telegram Mini App

React, TypeScript and Vite client for K-Loto. It authenticates every API request
with Telegram `initData`; balance, price, draw assignment and payout remain
server-authoritative.

```powershell
npm install
npm run dev
```

Vite proxies `/api` to `http://localhost:8000`. Open the production build only
through the Telegram bot menu button so signed `initData` is available.

`VITE_CART_TTL_SECONDS` controls local cart persistence. Until the owner resolves
the exact TTL, leave it blank; the cart then lasts only for the current open
Mini App session.
