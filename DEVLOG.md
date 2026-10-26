# Devlog

**English** · [Русский](DEVLOG.ru.md)

My notes on how Casper Loto is taking shape: decisions, experiments and
meaningful milestones. I develop the project on my own with AI assistance.
Entries use dates and titles; a journal entry is not an application release.

This is a concise account of the work. The complete earlier technical journal,
including local experiments, checks and deployment reports, is preserved in the
[history archive](docs/history/README.md). Product changes are in the
[Changelog](CHANGELOG.md), and future plans are in the [Roadmap](docs/ROADMAP.md).

## [Compact achievement popups and a quiet catalog] - 2026-10-26

The owner reported oversized achievement cards and continued popups after opening
the catalog. Removed both redundant text rows, reduced badge/padding and kept
CAS plus grouped ticket quantities in the compact reward line. Full reward details
remain in the achievement sheet. Catalog visibility suppresses the existing queue
and acknowledges fetched notices in batches of at most ten, including late arrivals.
Acks retain retry handling; no polling or backend change is added. New achievements
can notify normally after leaving the catalog. Only targeted frontend regressions,
lint/typecheck/build, mobile smoke and gateway publication checks apply.

## [Achievement notifications published] - 2026-10-23

Public 1.71.0, API/bot 1.60.0 and Mini App 1.71.0 were published under the
operations lock with VPS-only backups. Targeted feature checks and current-schema
preference migration passed; HTTPS, exact assets and health were verified.
The achievement launch epoch is unchanged and monitoring has no warnings.
See [release results](docs/releases/1.71.0.md).

## [Version approval for MAJOR only] - 2026-10-23

The owner now requires separate version-number approval only for MAJOR. MINOR
and PATCH releases follow the normal checks, backup, publication and health process
without an extra numbering question. Production was verified at 1.70.2; achievement
notification navigation and settings are prepared as compatible feature release
1.71.0. Historical release records retain their original wording.

## [Achievement notification navigation and settings] - 2026-10-23

Achievement popups and bell entries now open the exact achievement in its category.
A bounded catalog response can include the focused card independently of the first
page, preserving pagination and secret redaction. The profile has an independent,
persisted popup switch; re-enabling sets a UTC delivery boundary without changing
inbox history or rewards. Migration 0068 adds two preference fields.

Validation is limited to the affected UI tests, two isolated PostgreSQL regressions,
frontend lint/typecheck/build and backend static checks, as requested by the owner.
No full project suite was run. Prepared in an isolated branch so concurrent purchase
receipt work and previously local commits are excluded from this Git publication.
Public release/version approval and VPS deployment remain pending; see the
[implementation note](docs/achievements/NOTIFICATION_NAVIGATION.md).

## [Simpler backup storage for the current stage] - 2026-10-23

For now I am the only player, so I chose to keep backups on the VPS without
an automatic computer or cloud transfer. The approved storage policy keeps two
database copies, the running application plus two rollback versions per service,
and two recognised archives of each kind. Diagnostic logs keep their existing
retention. The maintenance tool applied this policy after the full GitHub checks,
Linux maintenance regressions and two complete restore rehearsals. Production
health passed, and running containers and data volumes were unchanged.
The game rules and public version 1.70.0 stay the same.

## [One public version for Casper Loto] - 2026-10-23

I have adopted **Casper Loto 1.70.0** as the shared public baseline for the
already released application. API, Mini App and Admin keep their own internal
versions. The Changelog uses the public product number; this journal continues
with dates and subjects. Earlier records remain available unchanged in the archive.

I approved the [versioning rules](docs/VERSIONING.md): compatible features use
a MINOR increase, compatible fixes use PATCH, and broken public compatibility
uses MAJOR. The next number must be agreed with me before a release. Documentation,
GitHub preparation and local work do not create another product version.

The [baseline record](docs/releases/1.70.0.md) maps the public version to the
verified component versions and deployment evidence. The approval follows the
earlier discussion recorded below. Opening the source repository does not need
a new game deployment or a GitHub Release.

## [Preparing the source for others to read] - 2026-10-23

I have put Casper Loto in a private GitHub repository while I prepare its public
page. The main README is in English, with Russian one click away. I used my own
iPhone screenshots and the existing logo, and kept my story in my own voice.

I chose MIT for my code and documentation so others can learn from and use the
project, including commercially. Casper Loto itself remains free of real-money
purchases. I also wanted the history to be readable: small related changes are
now grouped, and the complete technical notes remain available in an archive.
I am leaving the existing application version numbers unchanged while I decide
how I want future releases to be numbered.

The private repository has automated checks for the backend and both frontends.
This editorial work does not change game rules, balances or the running server.
The [verification note](docs/HISTORY_CLEANUP_2026-10-23.md) records the archive,
link and journal-loader checks.

## [An English interface] - 2026-10-23

Casper Loto can now be used in English as well as Russian. That includes the
games, achievements, rules and system messages, rather than just the navigation.
A player can change the language in the profile without restarting the app.
Draw schedules stay at UTC+3 in both languages.

Implementation was recorded on 22 October and production was verified on
23 October. The [technical report](docs/MINIAPP_LANGUAGES.md) keeps the details
and verification evidence together.

## [Two games with their own character] - 2026-10-22

Casper Mini and New Year Loto 2027 reached the running application. Mini has an
emerald number ticket; the New Year game uses illustrated objects and a paper
receipt. I revised the layout and artwork several times before publication.

I then refined the New Year purchase controls and mobile layout. Those small
follow-ups belong to the same story, so I have grouped them in the Changelog.
The [release report](docs/LOTTERY_RELEASE_2026-10-22.md) preserves the exact
technical versions and checks.

## [Achievements and a personal collection] - 2026-10-21

The achievement system reached production: 93 achievements in five rarities,
progress, one-time rewards, gift tickets, badges and themes. The profile brings
these together, and a separate catalogue makes them easier to explore.

The implementation was developed and checked locally in stages before the
production launch. I have kept the proposals, experiments and launch records
in the technical archive rather than describing each as a separate public release.

## [A consistent economy and a smaller application] - 2026-10-20

Between 18 and 20 October, the approved economy changes were published, the old
channel publication and Stories system was retired, and owner-reporting issues
were corrected. CAS movements continue to use the immutable ledger; completed
draws and purchases remain part of the history.

These are historical notes. The original reports remain available for following
the changes in detail.

## [Recovery, performance and different game worlds] - 2026-10-17

Earlier in October, work covered interrupted-purchase recovery, loading speed,
large ticket histories, monitoring and backups. The catalogue and games also
gained more individual presentation, including Aurora, Vault and the seasonal
game artwork. Some older web and publishing experiments were later retired.

The [historical overview](docs/history/README.md) groups the earlier work by
period and links to the complete original notes.

## [The first recorded stages] - 2026-08-15

The earliest project records cover the lottery engine, ledger, scheduler and
recovery, followed by the bot, Mini App, admin panel and first deployment.
The project has changed a great deal since then. I have preserved those records
with their original dates and numbers.

— **Andrey Kasper**
