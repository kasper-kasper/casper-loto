<p align="center"><strong>English</strong> · <a href="README.ru.md">Русский</a></p>

<p align="center">
  <a href="https://t.me/Kasper_loto_bot?startapp">
    <img src="frontend/shared/assets/brand/logo-horizontal.png" width="440" alt="Casper Loto">
  </a>
</p>

<h1 align="center">Luck costs nothing</h1>

<p align="center">
  Free lottery games in Telegram. Virtual currency, real excitement.
  <br>
  No donations, real-money bets or cash-out.
</p>

<p align="center">
  <a href="https://t.me/Kasper_loto_bot?startapp"><strong>Give it a try →</strong></a>
  &nbsp; · &nbsp;
  <a href="https://t.me/casper_loto">Project news</a>
  &nbsp; · &nbsp;
  <a href="https://t.me/rabochyru">Get in touch</a>
</p>

<p align="center">App languages: <strong>English · Русский</strong></p>

---

[About the game](#about-the-game) · [Screenshots](#screenshots) · [Getting started](#getting-started) · [My story](#my-story) · [Roadmap](#roadmap) · [For developers](#for-developers)

## About the game

**Casper Loto** is my independent project with number lotteries, quick draws,
instant games and seasonal events. Pick a combination, watch a draw, unlock
achievements and build a collection of badges and profile themes.

Everything runs on **CAS — a virtual game currency**. Tickets cost CAS and
prizes are paid in CAS. You cannot buy CAS with real money, cash it out or
exchange it for money. Every balance and jackpot you see in the app is virtual.

**There are no real-money purchases in Casper Loto, and there never will be.**
That is a principle of the project: no donations, paid CAS, paid tickets or
advantages bought with real money.

## Find your game

| If you want to… | Try… |
| --- | --- |
| Pick numbers and wait for a draw | 6 of 36, Casper Mini, Casper Grand and other number lotteries |
| Choose a ready-made card | Casper Bingo |
| Play a game in two stages | Casper Dual, with NIGHT and DAWN draws |
| Get a result quickly | Casper Fast: FLASH, CODE and PULSE |
| Reveal a ticket straight away | Instant games: Casper LIVE, Casper Aurora and Casper Vault |
| Enjoy a different atmosphere | Themed games, including Halloween and New Year Loto 2027 |
| Build your own progress | Achievements, rewards, badges and profile themes |

Each game has its own rules, visual style and prize categories.
In **Casper Fast**, a round takes place every **3 minutes**, with each of the
three games returning every **9 minutes**.

## Screenshots

I took these screenshots on my iPhone while putting this README together.
This is the game as it is, without mockups or retouching. I selected the
English interface here; the same screens are also available in Russian.
Click a screenshot to open it at full size.

<p align="center">
  <a href="assets/readme/today-iphone.png"><img src="assets/readme/today-iphone.png" width="240" alt="Today: the next Casper Dual draw, tickets and schedule"></a>
  &nbsp;
  <a href="assets/readme/lotteries-iphone.png"><img src="assets/readme/lotteries-iphone.png" width="240" alt="Game catalogue: New Year Loto 2027, Casper LIVE and Casper Aurora"></a>
  &nbsp;
  <a href="assets/readme/fast-iphone.png"><img src="assets/readme/fast-iphone.png" width="240" alt="Casper Fast: PULSE and FLASH with countdowns to their draws"></a>
</p>

<p align="center"><em>Today · Game catalogue · Casper Fast</em></p>

<details>
<summary><strong>Two more screens: other games and my account</strong></summary>

<br>

<p align="center">
  <a href="assets/readme/lotteries-more-iphone.png"><img src="assets/readme/lotteries-more-iphone.png" width="280" alt="Casper Vault, 6 of 36, Casper Mini, Casper Bingo, Casper Dual and Casper Grand"></a>
  &nbsp;
  <a href="assets/readme/account-iphone.png"><img src="assets/readme/account-iphone.png" width="280" alt="My account: virtual CAS balance, achievements, collection and active tickets"></a>
</p>

<p align="center"><em>Other games · My account</em></p>

</details>

These screenshots show my own account, with the balance and progress I have
already built up. A new player will have their own tickets, results and history.

## Getting started

1. [Open Casper Loto in Telegram](https://t.me/Kasper_loto_bot?startapp).
2. Choose a game and read its rules: the ticket price in CAS, schedule and
   winning conditions.
3. Get a ticket using virtual CAS. Wait for the result in a draw game,
   or reveal it straight away in an instant game.

You do not need to install a separate app or enter payment details.
All draw times are shown in **UTC+3 (Moscow time)**.

### English and Russian

The app already supports **English and Russian**. You can switch languages
under **My account → App language**, or
**«Личный кабинет → Язык приложения»**.

On your first visit, the app uses your Telegram language. If that is
unavailable, it uses your browser or device language. Your own selection
takes priority and is saved on that device. Other languages fall back to English.

## My story

Casper Loto is my first independent project. I work as a lawyer in Russia.
I am not a programmer and have not written a single line of code myself:
I build the app with the help of artificial intelligence. But the idea,
lottery rules, game economy and mechanics came from my own thinking.

There is a familiar saying: “The house always wins.” I want people to stop
spending real money on gambling. Waiting for a draw, an unexpected match and
the excitement of a win can exist without real-money bets.
That is where Casper Loto began.

I have rebuilt things many times after thinking they were finished.
I have changed rules, recalculated prizes and come up with new games.
I keep doing it because I enjoy it. Along the way, I am learning how all
of this works.

I did not create Casper Loto to make money. There are no donations,
purchases of virtual currency or ways to withdraw money. You cannot buy
anything with real money — now or in the future. I wanted to make a place
where people can try their luck, play and have a good time without putting
their own money on the line.

If you enjoy Casper Loto, want to play, suggest an idea, fix a bug or help
with development, I would be glad to hear from you.

For me, that would already mean it was worth doing.

Best regards,<br>
**Andrey Kasper** · [@rabochyru](https://t.me/rabochyru)

## How draws work

**Draws run on the Casper Loto server, using Python.** Random numbers and
outcomes come from `secrets.SystemRandom`, which draws randomness from the
operating system. You can read about it in the
[Python documentation](https://docs.python.org/3/library/random.html#random.SystemRandom).

The server determines an outcome under the game's rules, checks tickets
and records the prizes due. The app displays that result and its animation.
Tapping the screen or choosing when to reveal a ticket does not change the prize.
AI helps me build the app; it does not choose the winning numbers.

A draw keeps a snapshot of its rules, so later changes do not alter completed
draws. Every CAS movement is recorded in an immutable ledger. Duplicate
processing is guarded against, so retrying a request cannot pay the same prize
twice. Missed draws are recovered in chronological order.

I want the game to be understandable beyond my own description: the code
and implementation notes are available to study. See the
[architecture](docs/ARCHITECTURE.md), [rule strategies](docs/LOTTERY_STRATEGIES.md)
and [scheduler](docs/SCHEDULER.md). For the current conditions of an individual
game, check its rules in the app.

## Roadmap

I want each player to build their own history in Casper Loto.
These are the directions I am working towards:

- **Next-generation profiles:** a personal collection showcase, all-time
  statistics, rare rewards, a history of records and your own profile style.
- **Themed seasons:** collections, tasks and rewards brought together over
  roughly three months. Free progression, without a paid pass or pressure
  to log in every day.
- **Shared goals and communities:** challenges where players can help each
  other instead of always competing.
- **A transparency centre:** public draw statistics, past results,
  explanations of probabilities and an odds simulator in one place.
- **Public voting:** player suggestions and support for ideas inside
  the Mini App, ahead of a full lottery builder.
- **A lottery builder:** a way to put together and propose your own game.
- **An open API:** a way for other developers to build safe tools for Casper Loto.

I am building this on my own, one step at a time.
The [roadmap](docs/ROADMAP.md) has my current target dates.

## How to help

You do not have to be a developer. Play and tell me what you enjoyed,
explain what felt awkward, suggest a new game or help with writing,
translations and design. Help with code, testing, accessibility, security
and performance is welcome too.

When reporting a bug, describe what you did, what you expected and what
actually happened. The game name, time, device model and a screenshot
without private information can help. You do not need to send passwords
or sign-in codes.

- [Play in Telegram](https://t.me/Kasper_loto_bot?startapp)
- [Follow project news](https://t.me/casper_loto)
- [Suggest an idea, report a bug or help — @rabochyru](https://t.me/rabochyru)

## For developers

**Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic and aiogram.<br>
**Frontends:** React, TypeScript and Vite. **Deployment:** Docker Compose and Caddy.

Game rules and CAS accounting live on the server in domain and application
services. The Mini App, bot, admin panel and scheduler call those services.

<details>
<summary><strong>Structure, environment setup and checks</strong></summary>

### Structure

| Directory | Purpose |
| --- | --- |
| `backend/` | API, game rules, CAS accounting, migrations and tests |
| `frontend/miniapp/` | Player interface |
| `frontend/admin/` | Admin interface |
| `frontend/shared/` | Shared client modules and brand assets |
| `bot/` | Telegram bot entry point |
| `infrastructure/` | Gateway and HTTPS configuration |
| `scripts/` | Development, verification and operations commands |
| `docs/` | Documentation and plans |

Full [repository map](docs/REPOSITORY_LAYOUT.md).

### Set up the environment

You need **Python 3.12+**, **Node.js 22**, **PostgreSQL 16+** and `uv`.
Run these commands from the repository root:

```powershell
uv sync --locked --extra dev
npm --prefix frontend/miniapp ci
npm --prefix frontend/admin ci
```

Use [.env.example](.env.example) as a template, with your own local database
and local secrets. Real `.env` files, database dumps, backups and installed
dependencies do not belong in Git.

For a fresh checkout, follow the [local development guide](docs/LOCAL_DEVELOPMENT.md):
it covers PostgreSQL, the local `.env` and running the API with the Mini App.
The separate [Windows preview guide](docs/LOCAL_PREVIEW.md) describes my
already configured environment; a fresh computer will not have its desktop
shortcut. Browser mode does not require a real Telegram bot token.

### Checks

Run the full project checks on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

Checks that use PostgreSQL need a separate test database.
Each frontend also has `typecheck`, `lint`, `test` and `build` commands
in its `package.json`.

Read [AGENTS.md](AGENTS.md) before making changes.

</details>

## History and documentation

| Document | Contents |
| --- | --- |
| [Changelog](CHANGELOG.md) | Changes and releases; currently in Russian |
| [Devlog](DEVLOG.md) | Development notes, decisions and verification |
| [Roadmap](docs/ROADMAP.md) | Planned features and target dates, in English and Russian |
| [Documentation](docs/README.md) | Index of technical documentation |

Some technical and historical documents are currently in Russian.

## Licence

I want others to be able to learn from and use what I build. I am still
choosing a specific licence; its terms will appear in `LICENSE`.
Until then, [get in touch](https://t.me/rabochyru) about using the project.
Third-party dependencies, fonts and images have their own terms.

---

<p align="center">
  <strong>Casper Loto · Luck costs nothing</strong><br>
  <a href="https://t.me/Kasper_loto_bot?startapp">Give it a try →</a>
</p>
