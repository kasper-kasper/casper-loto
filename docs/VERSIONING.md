# Casper Loto versioning rules

**English** · [Русский](VERSIONING.ru.md)

The owner approved these project rules on 23 October 2026.
The current shared public version is **Casper Loto 1.71.1**, recorded in
[`VERSION`](../VERSION). API, Mini App and Admin retain independent internal
versions. The [1.70.0 baseline record](releases/1.70.0.md) maps them to the
shared public version.

## Semantic Versioning

The public version follows **MAJOR.MINOR.PATCH** and
[Semantic Versioning](https://semver.org/).

| Part | Increase when | Example |
| --- | --- | --- |
| MAJOR | A release breaks previously supported public application contracts | `1.71.0 → 2.0.0` |
| MINOR | A release adds compatible functionality, such as a game, quests, rankings or collections | `1.71.0 → 1.72.0` |
| PATCH | A release fixes bugs without breaking compatibility or adding functionality | `1.70.0 → 1.70.1` |

A MAJOR increase resets MINOR and PATCH to zero. A MINOR increase resets PATCH
to zero. Feature count, development time and the scale of a visual redesign
do not automatically require a MAJOR increase.

From the current release, the next compatible feature release is **1.72.0**;
the next fixes-only release is **1.71.2**. These are alternative next releases,
not releases that have already happened. Later numbers follow the latest
published public release; for example, a fix after 1.71.0 would be 1.71.1.

## Release and journal rules

1. Increase the public version for an actual release of changes to players,
   rather than for every commit.
2. Related small fixes may be grouped into one PATCH release.
3. Local development, testing, documentation edits and GitHub preparation do
   not by themselves increase the public version.
4. `CHANGELOG.md` has no separate version. Following
   [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), it records shared
   public Casper Loto releases under their own version numbers. The Russian
   counterpart uses the same release labels and dates.
5. Use `[Unreleased]` for player-facing changes not yet released to players.
   Keep completed repository/editorial work in the dated development notes.
6. `DEVLOG.md` has no version of its own. Use dates and subjects for entries;
   keep historical development-entry numbers in the archive.
7. Keep API, Mini App and Admin technical versions separately and record their
   relationship to each public release in technical documentation. They do not
   have to equal the public product version.
8. Preserve historical version numbers, entries, release snapshots and existing
   tags. The original Changelog and Devlog remain in the
   [history archive](history/README.md); older component-version headings below
   the 1.70.0 baseline are historical records.
9. Before a release, classify the changes and select the appropriate public
   version. MINOR and PATCH numbers may be selected and published without separate
   version approval. Obtain explicit owner approval only before increasing MAJOR,
   the first number, for example `1.x.x → 2.0.0`.
   The owner clarified this approval scope on 23 October 2026. Normal backup,
   checks, deployment and health verification rules remain in effect.
10. A GitHub Release/tag is optional for opening the source repository. Creating
    one is a separate release action; it does not justify a version increase
    or alter past deployment manifests.

## Initial public baseline

The version history starts at 0.1.0 on 14 August 2026 and reached 1.0.0 on
1 September 2026. Adoption of the shared public 1.70.0 baseline continues that
history. It does not reset the project to 1.0.0 or rename earlier releases.

The owner explicitly approved this baseline. The existing production snapshot
and package versions are preserved; only public version metadata and documentation
are being brought into agreement. GitHub visibility is changed separately by
the owner after review.
