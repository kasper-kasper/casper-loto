# K-Loto agent rules

These rules apply to every human or AI change in this repository.

1. Work only inside this repository. Do not deploy or connect to a production
   VPS without an explicit owner command.
2. Never commit secrets. Keep real tokens, passwords and credentials in `.env`;
   redact them from logs and documentation.
3. Do not invent unresolved business requirements. Record them in
   `docs/OPEN_DECISIONS.md` and wait for the owner.
4. Business history is immutable. Purchased tickets and completed draws are
   never edited or deleted. Corrections use explicit compensating/audit records.
5. A completed draw is never modified, including by an administrator.
6. Draw recovery is mandatory. Process missed draws chronologically and make
   scheduler/draw invocations idempotent with database transactions, locks and
   constraints.
7. Every CAS movement goes through the immutable ledger. Never silently replace
   a balance, jackpot, distribution fund or reserve value.
8. Keep business logic in domain/application services, never in API handlers,
   Telegram handlers, React code or scheduler callbacks.
9. Store timestamps in UTC and calculate official schedules explicitly in
   `Europe/Moscow`. Store CAS as integers, never floating point.
10. Add an Alembic migration for every schema change and tests for every domain
    rule or regression.
11. Before finishing a milestone, run formatter, linter, type checks and tests;
    document unavailable tools or checks.
12. Update `DEVLOG.md` after substantial work. Update `CHANGELOG.md` for visible
    changes and `docs/OPEN_DECISIONS.md` when decisions change.
13. Keep commits small, logical and meaningful. Never commit `.env`.
