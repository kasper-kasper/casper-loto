# Releases, Changelog and Devlog

**English** · [Русский](HISTORY_GUIDE.ru.md)

## Three different things

| Item | Meaning | Example |
| --- | --- | --- |
| Public application version | Identifies a released product state | Casper Loto `1.70.0` |
| Changelog entry | Describes notable changes in that release, using its number | What changed in Casper Loto `1.70.0` |
| Devlog entry | Explains development work and decisions, using a date and title | “An English interface”, 23 October 2026 |

Changelog has no independent version counter. Devlog entries do not create
application versions. A commit records a change in Git; it need not be a new
release or a separate journal entry. A GitHub Release packages a tagged state
with release notes; it need not be created for every commit.

## Approved public version and internal versions

The owner approved **Casper Loto 1.70.0** as the shared public baseline on
23 October 2026. It is recorded in [`VERSION`](../VERSION).
The independent internal package versions remain:

| Component | Existing version |
| --- | --- |
| API / Python package | `1.59.0` |
| Mini App | `1.70.0` |
| Admin | `1.61.2` |

The [versioning rules](VERSIONING.md) define SemVer and require owner approval
of each new public version. A compatible feature release after 1.70.0 would be
1.71.0; a fixes-only release would be 1.70.1. Documentation and GitHub preparation
alone do not increase the version. The [baseline record](releases/1.70.0.md)
maps the public version to verified deployment evidence. Past package manifests,
lockfiles, runtime versions, release snapshots and tags remain unchanged.

## How the history is edited

- Summarise related small fixes together. A range in a legacy heading lists
  existing releases; it does not invent a replacement release.
- Keep original numbers and dates in the complete historical records.
- Keep local experiments and proposals in the development history; describe
  them as released features only when release evidence exists.
- Public Changelog and Devlog have English and Russian counterparts. The old
  technical records retain their original languages in the archive.
- Keep implementation dates distinct from deployment dates. For example,
  English Mini App work was recorded on 22 October and production verified
  on 23 October.

The [history archive](history/README.md) contains byte-for-byte snapshots of
both original journals, with a hash and heading index. Existing root journal
filenames and bracketed heading syntax remain readable by the admin journal
loader. This documentation change is available on the VPS with a later normal
application publication; it does not require rebuilding the running game.

## Conventions and examples

[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) is a widely used
recommendation for a curated list of notable changes, an Unreleased section,
dates and release headings. It is not a rule that every code edit needs a release.

[Semantic Versioning](https://semver.org/) defines `MAJOR.MINOR.PATCH` in terms
of compatibility with a declared public API: incompatible changes, compatible
features and compatible fixes. It does not prescribe an independent number
for a changelog or a specific next version for this project.

For examples, [VS Code release notes](https://code.visualstudio.com/updates)
are grouped by product release; the [React blog](https://react.dev/blog)
contains dated announcements and development articles.
[GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
are based on Git tags. These are different tools for communicating project history.
