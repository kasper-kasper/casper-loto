# Telegram bot and Mini App

`/start` idempotently binds the Telegram identity, brings its total automatic
welcome allocation to 100,000,000,000 CAS through the immutable ledger and
immediately offers the signed Mini App. A persistent **Играть в K-Loto** button
beside the Telegram message field opens the Mini App in one tap.

The bot is now the notification and entry channel. New player journeys do not
use its legacy button gameplay: selection, checkout, tickets and results live in
the Mini App. Historical handlers remain temporarily dormant for compatibility
with old messages and do not contain financial business rules.

The Mini App is the primary visual player interface. It shows authoritative
balance and jackpots for all active lotteries, Moscow countdowns, number pickers,
mixed-lottery cart, purchases and ticket history. Its production design uses a
premium blue/red/gold palette and automatic Telegram authentication.

Purchase/result notifications use a durable outbox. Event keys prevent duplicate
sends. Every notification includes a direct Mini App button. Empty draws notify
every active non-admin Telegram player that no one participated and show the
current jackpot.
