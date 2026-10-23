# K-Loto agent rules

These rules apply to every human or AI change in this repository.

1. Work only inside this repository. After a completed release passes all
   required checks, back it up and deploy it to the configured production VPS,
   then verify production health. Skip deployment only when the owner explicitly
   requests local-only work or deployment is unsafe or blocked.
2. Never commit secrets. Keep real tokens, passwords and credentials in `.env`;
   redact them from logs and documentation.
3. Do not invent unresolved business requirements. Record them in
   `docs/OPEN_DECISIONS.md` and wait for the owner.
4. Completed business history is immutable. Purchased tickets are never deleted.
   With explicit owner approval, tickets in future draws may receive a full
   ledgered refund and move to `REFUNDED` during a format transition. Every such
   correction must use explicit compensating ledger and audit records.
5. A completed draw is never modified, including by an administrator.
6. Draw recovery is mandatory. Process missed draws chronologically and make
   scheduler/draw invocations idempotent with database transactions, locks and
   constraints.
7. Every CAS movement goes through the immutable ledger. Never silently replace
   a balance, jackpot, distribution fund or reserve value.
8. Keep money, draw, auth and other business rules in domain/application
   services. API handlers, Telegram handlers, React components and scheduler
   callbacks may orchestrate presentation and calls to those services, but may
   not implement or duplicate the authoritative rules.
9. Store timestamps in UTC and calculate official schedules explicitly in
   `Europe/Moscow`. Store CAS as integers, never floating point.
10. Add an Alembic migration for every schema change and tests for every domain
    rule or regression.
11. Match checks to risk while developing: visual experiments, CSS, SVG, Canvas,
    WebGL, animation and other presentation work use the affected frontend's
    lint/typecheck/build and a focused smoke test; isolated UI behavior adds the
    affected frontend tests. Money, draws, scheduler, database, auth and
    security changes use the full project suite. Do not block visual work on
    unrelated backend checks; run the full required suite once before a release
    and document unavailable checks.
12. Update `DEVLOG.md` after substantial work. Update `CHANGELOG.md` for visible
    changes and `docs/OPEN_DECISIONS.md` when decisions change.
13. Keep commits small, logical and meaningful. Never commit `.env`.
14. Rebuild and redeploy only services affected by a change when that is safe.
    Group related minor copy changes into one PATCH release; reserve CHANGELOG
    entries for visible product changes and DEVLOG entries for substantial work.

15. After any requested product change that passes the smallest relevant checks,
    publish it immediately to the configured production VPS and verify production
    health. Do not leave completed user-requested changes only in the worktree.
    For frontend-only work, run the affected frontend typecheck/lint/build,
    deploy `gateway`, and perform the configured health check. Skip publication
    only when the owner explicitly requests local-only work or deployment is
    unsafe/blocked; report that blocker clearly.

16. There is no visual technology restriction. UI work may use React, CSS,
    SVG, Canvas, WebGL, Phaser, Three.js, generated raster assets and custom
    animation when that improves the product. Keep heavy engines isolated to
    the experience that needs them, preserve keyboard/accessibility fallbacks
    for important controls, and keep authoritative business state on the
    server.

17. VPS publications must hold `/run/lock/k-loto-operations.lock` for their
    entire backup/upload/build/restart/health sequence. Use
    `scripts.vps_operation_lock.remote_operations_lock` for SSH releases.
    Preserve API/bot diagnostic logs with `archive_diagnostic_logs()` under
    that lock before recreating either service.
    Storage cleanup belongs to `scripts/server_maintenance.py`; do not add
    broad Docker pruning or volume deletion to release helpers. Compact
    retention settings and when to increase them are in `docs/SERVER_STORAGE.md`.

18. The October 2026 local economy accumulation window is complete (OD-065).
    The owner explicitly authorized final checks, deployment and reopening.
    Normal release rules apply again. Do not repeat the completed ticket refunds,
    reset draw/ticket counters, or reapply the economic transition as a new epoch.
    Future maintenance windows require a new owner instruction.

19. Preserve owner-approved thematic CAS amounts exactly; never round ticket
    prices, jackpots or prizes to tens/hundreds/thousands. All monetary operations
    use integer arithmetic. For a 50% ticket-to-jackpot allocation, round each
    ticket's contribution upward and burn the integer remainder (3,333 CAS means
    1,667 to jackpot and 1,666 burned). Bulk/multi-draw purchases sum these
    per-ticket contributions; do not round half of the combined purchase instead.

20. Follow `docs/VERSIONING.md` (Russian: `docs/VERSIONING.ru.md`). The owner-approved
    shared public baseline is Casper Loto 1.70.0, recorded in `VERSION`; internal
    API, Mini App and Admin versions remain independent. CHANGELOG describes
    shared public product releases and has no version of its own. DEVLOG entries
    use dates and subjects, without a new journal-version sequence. Preserve
    all historical numbers, records, release manifests and tags. Use Unreleased
    for player-facing changes not yet published. Documentation, GitHub preparation,
    testing and local work alone do not increase the public version. Before a
    product release, classify the changes and select the appropriate SemVer number.
    MINOR and PATCH releases may be numbered and published without separate version
    approval. Obtain explicit owner approval only before increasing MAJOR (the
    first number, for example 1.x.x to 2.0.0). A major visual update or feature
    count alone does not require MAJOR. This approval scope was updated by the
    owner on 23 October 2026; normal backup, checks and deployment rules still apply.

21. The owner-approved 2026-10-23 storage profile is VPS-only: two newest validated
    database dumps; current/referenced application images plus two previous tagged
    rollback versions per service; two recognized release archives per category.
    Keep diagnostic logs under their separate 90-day policy. Do not add automatic
    computer/cloud backup transfers unless the owner requests a new policy.
    Apply retention only through the locked, guarded maintenance tool; never delete
    purchased tickets, draws, ledger history, live volumes or unknown files.
