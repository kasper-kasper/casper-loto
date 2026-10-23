# Changelog

**English** · [Русский](CHANGELOG.ru.md)

Notable changes to Casper Loto, newest first. Entries describe product releases;
this document has no version number of its own. Related small changes are
summarised together, with their original release numbers preserved.

The shared public baseline is **Casper Loto 1.70.0**, recorded in
[`VERSION`](VERSION). API, Mini App and Admin keep their independent internal
versions. Earlier component-version headings remain historical records.
See the [approved versioning rules](docs/VERSIONING.md) and
[journal guide](docs/HISTORY_GUIDE.md).

## [Unreleased]

## [1.71.0] - 2026-10-23

### Added

- An independent in-app achievement notification switch below the profile language
  selector. Achievement history remains available in the bell when popups are off.

### Fixed

- Achievement notifications now open the relevant category and achievement details,
  including achievements beyond the first catalog page. The selected card stays
  highlighted after closing its details.
- Popups allow more reading time and pause while interacting. Re-enabling popups
  does not replay achievements earned while they were disabled.

Public **1.71.0**; API **1.60.0**, Mini App **1.71.0**, Admin **1.61.2**.
[Release record](docs/releases/1.71.0.md).


## [1.70.0] - 2026-10-23

**Casper Loto 1.70.0** is the first shared public baseline for the existing
released application. Internal components: API **1.59.0**, Mini App **1.70.0**,
Admin **1.61.2**. See the [baseline record](docs/releases/1.70.0.md).
The shared public designation was adopted on 23 October; no additional
game deployment is implied by this documentation update.

### Added

- English across the catalogue, games, tickets, live draws, archive, profile,
  achievements, rules and system messages.
- A profile language switch that updates the interface without reloading.
  A saved choice takes priority, followed by Telegram and device language.

### Changed

- Dates and numbers follow the interface language; draw schedules remain UTC+3.

Implementation was recorded on 22 October; production was verified on 23 October.
See the [release report](docs/MINIAPP_LANGUAGES.md).

## [API 1.59.0 / Mini App 1.69.0–1.69.1] - 2026-10-22

### Added

- Casper Mini and New Year Loto 2027, each with its own rules, tickets, draws
  and visual identity.
- A dedicated emerald number ticket for Mini and an illustrated symbol ticket
  for the New Year game, including their live draws and results.

### Changed

- New Year quick purchases, five-draw selection and illustrated favourites.
- Mobile sizing that keeps the symbol field and purchase controls accessible
  within Telegram, plus a full-width seasonal catalogue card.

The two adjacent Mini App releases are summarised together here; they retain
their original numbers. [Production report](docs/LOTTERY_RELEASE_2026-10-22.md).

## [API 1.58.0–1.58.2 / Mini App 1.68.0–1.68.2] - 2026-10-21

### Added

- 93 achievements across five rarities, with progress, one-time CAS rewards,
  gift tickets and a collection of badges and profile themes.
- A compact profile and an achievement catalogue with filters and details.

### Fixed

- Achievement activation no longer delays a game operation already in progress.
- Startup shows normal loading while server availability is being checked.
  The maintenance screen appears only after maintenance is confirmed.
- Clearer owner summaries and consistent operational warnings.

These releases and their follow-up fixes form one summary. The original
release and activation records remain in the
[technical archive](docs/history/2026-10-23/DEVLOG.original.md).

## [API 1.57.0–1.57.2 / Mini App 1.67.0–1.67.1 / Admin 1.61.0–1.61.2] - 2026-10-20

### Changed

- Consolidated the approved economy update across the existing games,
  preserving exact integer CAS amounts and ledger records.
- Retired the former channel publication, Stories and feed features.

### Fixed

- Owner daily-summary delivery and the display of distribution draw matches.

This summary covers the recorded releases of 18–20 October. It does not
repeat the economy transition or change completed draws and purchases.

## [Earlier releases] - 2026-10-17

Earlier work is grouped into readable milestones in the
[historical overview](docs/history/README.md): purchase recovery, performance,
new games, mobile presentation and the initial application foundation.
The overview links to every original heading and version in the preserved logs.

---

Editorial approach: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Dates in older records are retained as recorded; a development-note date alone
is not proof of a production deployment.
