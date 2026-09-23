# Telegram bot and Mini App

`/start` idempotently binds the Telegram identity, brings its total automatic
welcome allocation to 100,000,000,000 CAS through the immutable ledger and
immediately offers the signed Mini App. A persistent **Играть в Casper Loto** button
beside the Telegram message field opens the Mini App in one tap.

The bot is now the permission-based notification and entry channel. New player
journeys do not use its legacy button gameplay: selection, checkout, tickets
and results live in the Mini App. Historical handlers remain temporarily
dormant for compatibility with old messages and do not contain financial
business rules.

The Mini App is the primary visual player interface. It shows authoritative
balance and jackpots for all active lotteries, Moscow countdowns, number pickers,
mixed-lottery cart, purchases and ticket history. Its production design uses a
premium blue/red/gold palette and automatic Telegram authentication.

After a successful purchase the Mini App may call Telegram's native
`requestWriteAccess` prompt. Only an affirmative answer enables messages. The
player can later turn either category off in «Моё».

The durable outbox sends exactly two player-facing categories:

- a result for a completed draw where that player owned at least one ticket;
- an inactivity reminder after 24 hours without a new purchase.

There is no separate purchase message, no result broadcast for empty draws and
no Telegram message for a draw the player did not enter. Event keys prevent
duplicate sends and every delivered message keeps a direct Mini App button.
