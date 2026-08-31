# Telegram bot and Mini App

`/start` idempotently binds the Telegram identity and brings its total automatic
welcome allocation to 100,000,000,000 CAS through the immutable ledger. `/menu`
opens gameplay and `/web` opens the signed Telegram Mini App (the command name is
kept for compatibility).

The bot supports lottery/draw choice, manual or secure random numbers,
multi-ticket checkout, favourites, balance, active/history tickets, results,
statistics and rules. Purchases call application services and never implement
money logic inside handlers.

The Mini App is the primary visual player interface. It shows authoritative
balance and jackpots for all active lotteries, Moscow countdowns, number pickers,
mixed-lottery cart, purchases and ticket history. Its production design uses a
premium blue/red/gold palette and automatic Telegram authentication.

Purchase/result notifications use a durable outbox. Event keys prevent duplicate
sends. Empty draws notify every active non-admin Telegram player that no one
participated, show the current jackpot and include a button opening the exact
lottery's next available draw.
