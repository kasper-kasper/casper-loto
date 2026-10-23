# Devlog

**English** · [Русский](DEVLOG.ru.md)

My notes on how Casper Loto is taking shape: decisions, experiments and
meaningful milestones. I develop the project on my own with AI assistance.
Entries use dates and titles; a journal entry is not an application release.

This is a concise account of the work. The complete earlier technical journal,
including local experiments, checks and deployment reports, is preserved in the
[history archive](docs/history/README.md). Product changes are in the
[Changelog](CHANGELOG.md), and future plans are in the [Roadmap](docs/ROADMAP.md).

## [Simpler backup storage for the current stage] - 2026-10-23

For now I am the only player, so I chose to keep backups on the VPS without
an automatic computer or cloud transfer. The approved storage policy keeps two
database copies, the running application plus two rollback versions per service,
and two recognised archives of each kind. Diagnostic logs keep their existing
retention. The change is being checked and applied through the maintenance tool;
the game rules and public version 1.70.0 stay the same.

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
