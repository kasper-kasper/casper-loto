# Journal cleanup and MIT — 23 October 2026

The owner approved MIT and asked to group small changes into readable history.
They subsequently instructed that application numbering must remain unchanged
until a separate decision. See OD-081 and OD-082 in
[OPEN_DECISIONS.md](OPEN_DECISIONS.md).

## Result

- Standard MIT text in [LICENSE](../LICENSE), copyright 2026 Andrey Kasper;
  bilingual licensing explanations and updated README links.
- English and Russian public Changelog and Devlog. Recent related patch releases
  share summaries with original numbers retained. Older work has a dated overview.
- Two complete original Git blobs preserved in [the archive](history/README.md).
  Its [index](history/2026-10-23/index.json) records the original commit, SHA-256,
  and all level-one/level-two headings, including nonstandard headings.
- Implementation and deployment dates distinguished for Mini App 1.70.0.
- No application, dependency, schema, CI, release-tool or version-metadata changes.

## Verification

- Compared the archive bytes to Git commit
  `4ab94855ac85dd2b2a08ac8c2551d0a06bba856a`; both match exactly.
- Compared all seven version-bearing source and lock files with that commit;
  all remain unchanged. API 1.59.0, Mini App 1.70.0, Admin 1.61.2.
- Loaded both current root journals through the existing administrator read model.
  English/Russian entry dates match; Changelog release labels match; no empty entries.
- Existing release-note regression suite: **3 passed**. The clean Python 3.14
  test environment emits one pytest-asyncio deprecation warning.
- Checked 211 local Markdown links across the edited public documents.
- Rendered both READMEs at 320/390/1280px in light/dark themes; no missing images,
  page overflow or broken in-page anchors. Rendered eight journal/licensing pages
  at 320px dark and 1280px light; no page overflow. Screenshots visually inspected.
- Repeated the secret scan against prospective source files and reachable Git
  history; no known current-secret values or token/private-key pattern matches.

Local verification scripts, screenshots and detailed reports remain ignored
under `.tools/readme-review/`. No new application release or production deployment
is performed for this documentation-only task. Repository visibility remains private.
