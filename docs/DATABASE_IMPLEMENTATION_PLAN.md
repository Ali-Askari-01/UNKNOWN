# SQL Server Database Implementation Plan

## Phase 0 — decisions and readiness

Deliverables: approved scoring policy, privacy/consent policy, SQL Server target, media storage decision, RPO/RTO, operator roles.

Exit criteria: no unresolved decision affects table shape or permissions.

## Phase 1 — local database foundation

1. Install SQL Server Developer/Express and ODBC Driver 18.
2. Create `unknown_dev` and a least-privilege application login.
3. Add Alembic or the selected migration runner.
4. Apply `001_initial_schema.sql` to a clean database.
5. Add connection health and migration-version checks.

Exit criteria: fresh database creation is repeatable and health checks pass.

## Phase 2 — seed and import

1. Seed roles, event edition, IX/X/XI, rounds, and controlled vocabulary.
2. Build idempotent import for verified teams and members.
3. Build question staging/import validation.
4. Import only reviewed demo data locally.
5. Produce row-count and rejected-row reports.

Exit criteria: current demo teams/questions are queryable and import can run twice safely.

## Phase 3 — repository implementation

Implement SQL repositories for teams, questions, quiz sessions, participants, answers, and score entries. Preserve the existing service interfaces where possible. Add transaction abstractions and explicit `commit/rollback` behavior.

Exit criteria: repository integration tests pass without in-memory repositories.

## Phase 4 — persistence cutover behind a flag

1. Add `STORAGE_BACKEND=memory|sqlserver`.
2. Run read-only SQL queries alongside memory in staging and compare projections.
3. Enable SQL writes for teams/questions first.
4. Enable quiz sessions and score ledger.
5. Disable memory writes after a stable soak period.

Exit criteria: restart does not lose state and projections match the reference dataset.

## Phase 5 — production readiness

Backups, restore rehearsal, indexes/query plans, permissions review, audit review, load test, monitoring, and event-day runbook.

Exit criteria: approved go-live checklist and tested rollback.
