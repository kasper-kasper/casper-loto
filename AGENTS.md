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

15. There is no visual technology restriction. UI work may use React, CSS,
    SVG, Canvas, WebGL, Phaser, Three.js, generated raster assets and custom
    animation when that improves the product. Keep heavy engines isolated to
    the experience that needs them, preserve keyboard/accessibility fallbacks
    for important controls, and keep authoritative business state on the
    server.
