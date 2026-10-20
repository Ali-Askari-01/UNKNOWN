# Current Architecture

Status: implemented service-backed runtime. This document describes the production path; the
retired Node/Socket.IO and in-memory implementation is not part of the application.

## Runtime topology

```text
Browser
  ├─ Next.js landing, auth, admin and student pages
  ├─ same-origin /api/v1/* rewrite ───────► FastAPI
  └─ native WebSocket /api/v1/ws/* ───────► FastAPI
                                               ├─ SQLAlchemy async session
                                               └─ SQL Server / SQLite development database
```

Next.js is the presentation and same-origin proxy layer. FastAPI is the sole authority for
authentication, quiz lifecycle, team participation, question data, buzzer arbitration, answer
judging, scoring, leaderboards, audit records, and realtime snapshots.

## Backend boundaries

- `app/api/v1/` contains versioned HTTP and WebSocket adapters.
- `app/core/` contains settings, authentication, request IDs, rate limiting, error handling, and
  structured request logging.
- `app/db/` contains SQLAlchemy models and the async engine/session factory.
- `app/repositories/` contains persistence queries and domain-facing data access.
- `migrations/` contains reviewed Alembic revisions.
- `scripts/` contains bounded operational checks and seed/load tools.

The browser never supplies authoritative score, winner, participant identity, answer correctness,
or lifecycle state. The backend derives those values from authenticated identity and persisted
state.

## Authentication and authorization

- Admin login verifies a bcrypt hash and issues a signed, HttpOnly cookie.
- Team join validates quiz code, session, class, and team membership before issuing a scoped,
  HttpOnly team cookie.
- HTTP mutations and WebSocket connections require the appropriate signed identity.
- Production rejects default secrets, SQLite, missing bcrypt admin hashes, and development admin
  bypass.
- CORS is an explicit allowlist and trusted hosts are configured separately.

## Quiz consistency

- Lifecycle transitions are persisted and audited.
- Buzzer presses are persisted with a database-enforced one-winner constraint per question.
- Answer submissions remain pending until an authenticated administrator judges them.
- Only judged answers produce score ledger entries.
- Public responses omit answer keys, private fields, and future questions.
- Realtime messages are sanitized snapshots/events with sequence numbers; clients are renderers,
  not authorities.

## Operations

- Web containers do not migrate the database by default. Set `BACKEND_RUN_MIGRATIONS=true` only
  for a controlled migration operation; normal releases use a separate migration identity.
- SQL-backed rate-limit events and locked bucket rows coordinate multiple API workers.
- Production/staging SQL Server engines use bounded connection pools configured by
  `BACKEND_DB_POOL_SIZE`, `BACKEND_DB_MAX_OVERFLOW`, `BACKEND_DB_POOL_TIMEOUT`, and
  `BACKEND_DB_POOL_RECYCLE`; local/test engines use `NullPool` for loop isolation.
- Every request receives or preserves an `x-request-id`; structured logs include request ID, route,
  status, and duration without cookies or request bodies.
- `/health/live` checks process liveness and `/health/ready` checks database readiness.
- Release order, backup/restore rehearsal, migration verification, smoke tests, and rollback
  controls are documented in [PRODUCTION_RELEASE_RUNBOOK.md](PRODUCTION_RELEASE_RUNBOOK.md).

See [REALTIME_EVENTS.md](REALTIME_EVENTS.md), [QUIZ_FLOW.md](QUIZ_FLOW.md), and
[INTEGRATION_AUDIT.md](INTEGRATION_AUDIT.md) for the detailed contracts and current evidence.
