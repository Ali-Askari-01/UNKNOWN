# Delivery Roadmap and Remaining Gaps

## Completed implementation phases

1. **Contract and runtime baseline** — versioned FastAPI HTTP/WebSocket contracts, strict frontend
   type checking, CI, environment validation, health endpoints, request IDs, and the standard
   Next.js runtime.
2. **Persistence and authentication** — SQLAlchemy/Alembic models, SQL Server integration, bcrypt
   admin authentication, scoped team tokens, authorization boundaries, and audit records.
3. **Durable quiz vertical slice** — question bank, quiz blueprints, session lifecycle, participant
   registration, database-confirmed buzzer arbitration, pending answers, judging, score ledger, and
   leaderboard.
4. **Realtime and security hardening** — native authenticated WebSocket snapshots, shared SQL-backed
   rate limiting, trusted hosts, CORS allowlists, sanitized public responses, and production secret
   validation.
5. **Release operations** — backup/restore runbook, migration preflight, migration-head readiness,
   structured request logs, explicit migration execution, Docker/CI image-liveness checks, and
   bounded production DB pooling plus idempotent session actions, team join, answer submission, and
   judging.

## Remaining release gates

- Run the backup/restore rehearsal against the actual production database after migration
  `0010_auto_quiz_rules`, and retain row-count, audit-continuity, and readiness evidence.
- Run a production-style soak/load test with real event content, multiple API workers, WebSocket
  reconnects, rate-limit coordination, and database pool monitoring.
- The bounded repository soak harness is locally proven against SQLite and SQL Server; the same
  harness still requires execution against the production-like multi-worker deployment for release
  sign-off.
- The container accepts bounded `BACKEND_WORKERS` (1–8). The hosted default remains one worker;
  staging must run the soak at the planned worker count with shared SQL Server rate-limit and
  idempotency state before the deployment setting is raised.
- Verify deployment secret-manager injection, bcrypt hash rotation, CORS/trusted-host values,
  alert routing, log retention, and operator access in the production environment.
- Run the scoped FastAPI-owned schema contract check as part of every production migration
  rehearsal; legacy tables remain explicitly outside the application ownership boundary.
- Monitor `/health/ready` relay diagnostics and alert when a worker reports a stopped relay or a
  stagnant realtime event cursor.
- Complete an event-day rehearsal covering admin login, session creation, lifecycle actions, team
  join, buzzer race, answer submission, idempotent judging retry, leaderboard publication, and
  rollback/restore procedures.

## Product decisions still requiring an owner

- Final scoring policy: tie breaks, negative marking, bonus points, and score overrides.
- Student privacy/consent, retention, deletion, and public-name/photo policy.
- Object-storage provider and media upload limits if media is introduced.
- Operator roles and the authorization policy for manual score overrides.

The repository is locally connected and verifiable, but production cutover remains gated on the
environment-specific operational evidence above.
