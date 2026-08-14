# Telegram player bot

Planned for Milestone 4 using aiogram 3.x. The bot is a transport adapter: it
must not own ticket, balance, draw or payout rules. Telegram identity will map
to a normal backend `User` entity, and Telegram `initData` or bot updates must
be validated server-side.
