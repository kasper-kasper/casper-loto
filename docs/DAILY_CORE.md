# Daily Lottery 4/15

ПЛЛ-лото (`pll`), ПСС-Лото (`pss`) and ХАН-Лото (`khan`) are independent
lottery entities. Their Moscow times are 02:22, 12:00 and 18:00 respectively;
sales close two minutes before each draw. Each has independent draw and ticket
number sequences and independent jackpot, distribution and reserve accounts.

For each ticket, 40% of price enters jackpot and 60% enters distribution.
Payouts are 0 for 0/4 and 1/4, 50% of ticket price for 2/4, 300% for 3/4, and
the entire jackpot split equally among 4/4 tickets. Guaranteed distribution
payout shortage uses reserve and never jackpot. Remainders carry over. After a
4/4 win, jackpot resets to that lottery's Admin-configured base.

Identical combinations are allowed as separate tickets. RNG uses
`secrets.SystemRandom`. Empty draws still complete, carry all funds and generate
an idempotent Telegram broadcast.

At v0.14.0 PSS and KHAN start with 24,000,000 CAS base/current jackpots and zero
distribution/reserve. PLL inherits the shared Daily balances after its already
purchased legacy draw settles. All transfers use paired ledger entries.
