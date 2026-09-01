# Daily Lottery 4/15

ПЛЛ-лото (`pll`), ПСС-Лото (`pss`) and ХАН-Лото (`khan`) are independent
lottery entities. Their Moscow slots are PLL 02:22/13:45, PSS 12:00/20:30 and
KHAN 09:00/18:00;
sales close two minutes before each draw. Each has independent draw and ticket
number sequences and independent jackpot accounts.

For each new ticket, 100% of price enters jackpot.
Payouts are 0 for 0/4 and 1/4, 50% of ticket price for 2/4, 300% for 3/4, and
the entire jackpot split equally among 4/4 tickets. Lower-tier payouts use the
central Kasper Fund and never jackpot. After a
4/4 win, jackpot resets to that lottery's Admin-configured base.

Identical combinations are allowed as separate tickets. RNG uses
`secrets.SystemRandom`. Empty draws still complete, carry all funds and generate
an idempotent Telegram broadcast.

At v0.14.0 PSS and KHAN start with 24,000,000 CAS base/current jackpots and zero
distribution/reserve. PLL inherits the shared Daily balances after its already
purchased legacy draw settles. All transfers use paired ledger entries.

## «3 СЕНТЯБРЯ» 3/33

`september` is a separate Daily entity with draws at 03:33 and 15:33 Moscow,
a two-minute cutoff and independent draw/ticket numbering. A ticket costs
333 CAS and contains exactly three unique numbers from 1 through 33.

Payouts are 0 for 0/3, 333 CAS for 1/3 and 3,333 CAS for 2/3. The fixed main
prize of 33,333,333 CAS is split deterministically among all 3/3 tickets. Ticket
sales enter jackpot; fixed lower-tier prizes use the Kasper Fund. After a main
prize win, the Kasper Fund refills it to 33,333,333 CAS, so the displayed prize
does not accumulate, shrink or reset to another value. The approved initial
reserve is 1,000,000,000 CAS.

## «ГРОБ» 3/16

`grob` is a separate Daily entity with draws at 06:06 and 23:06 Moscow, a
two-minute cutoff and independent draw/ticket numbering beginning at one. A
ticket costs 6,666 CAS and contains exactly three unique numbers from 1 through
16.

Payouts are 0 for 0/3, 666 CAS for 1/3 and 6,666 CAS for 2/3. Fixed payouts use
the Kasper Fund; jackpot is never used for them. All 3/3 tickets split the
current jackpot deterministically. An unclaimed jackpot carries over; after a 3/3 win the jackpot resets
to its Admin-configured base, initially 6,666,666 CAS.

All CAS stays integer. Each new ticket contributes its full 6,666 CAS to the
jackpot. A bulk purchase has exactly the same accounting result as separate purchases.
