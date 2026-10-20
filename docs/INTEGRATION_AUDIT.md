# Integration Audit

Date: 2026-10-20

## Verified locally

| Boundary | Result | Evidence |
|---|---|---|
| Next.js frontend build | Pass | `pnpm build` completes successfully |
| FastAPI liveness | Pass | `GET /health/live` returns HTTP 200 |
| FastAPI readiness | Pass on SQL Server Express | `GET /health/ready` returns HTTP 200 with `database: ok` |
| FastAPI OpenAPI | Pass | `/openapi.json` is generated |
| FastAPI tests | Pass | 38 tests pass |
| Alembic migration discovery | Pass locally | `0010_auto_quiz_rules` is the application release head; it adds accepted-answer snapshots for automatic grading |
| SQL Server connectivity | Pass locally | SQL Server Express `SQLEXPRESS`, ODBC Driver 18, database `UNKNOWN`, was last verified at migration `0009_question_content_snapshots`; apply migration `0010_auto_quiz_rules` before using the updated quiz workflow |
| Live Next.js-to-FastAPI runtime | Pass locally | Landing, quiz, admin login, protected admin redirect, `/api/v1/classes`, `/api/v1/teams`, and authenticated admin page checks returned expected responses |

## Current implementation evidence

- The backend now has 36 passing tests against the configured SQL Server database, covering
  authentication identity and bcrypt hashes, question privacy, blueprint validation, session
  generation, public quiz-code lookup, participation, scoring, duplicate answers, concurrent
  buzzer arbitration, and audit behavior.
- The authenticated `/admin/questions` frontend now uses the versioned question-bank endpoints
  for database-backed listing and creation; MCQ options and class-track assignment are validated
  by the FastAPI schema.
- Authentication, team join, buzzer, and answer writes use SQL-backed sliding-window rate limits;
  per-bucket row locking coordinates concurrent API workers.
- Two-worker FastAPI smoke passed the five-team buzzer race against SQL Server with one `201`
  winner and four controlled `409` conflicts.
- Cross-manager realtime relay test passed: an event published by one manager was delivered to a
  WebSocket owned by another manager through the shared SQL Server event table.
- Realtime event insertion is serialized by a transaction-held database lock row, preserving
  identity commit order across workers; a two-transaction SQL Server regression test verifies the
  second writer waits and receives the next event ID.
- `quiz_soak_smoke.py` completed two concurrent end-to-end sessions against both SQLite and SQL
  Server, with reconnect and score-publication invariants true for every iteration.
- `backend/scripts/production_preflight.py` validates production-only settings, database
  connectivity, the installed Alembic head, and every FastAPI-owned table/column without exposing
  secrets or attempting to remove unrelated legacy objects.
- A production-configured worker returned HTTP 200 from `/health/ready` with the SQL-backed relay
  reporting `relayRunning: true` against local SQL Server.
- Render's API health check targets the actual unversioned `/health/ready` route, and the web
  container has migrations disabled by default to avoid concurrent rolling-release upgrades.
- Structured request logs include correlation IDs and latency while excluding cookies and bodies.
- HTTP security-header checks pass for liveness responses, including production-only HSTS behavior.
- Admin answer judging accepts an `Idempotency-Key`, replays the stored response for safe retries,
  and rejects reuse with a different payload.
- Team join and answer submission also accept durable idempotency keys; the student browser sends
  deterministic keys and the E2E smoke verifies replayed responses.
- Admin lifecycle actions accept deterministic idempotency keys from the control panel, preventing
  a lost response from causing a second transition attempt.
- Session lifecycle writes now use optimistic concurrency with a persisted row version; stale
  competing requests receive `409 SESSION_STATE_CHANGED`. Migration `0007_quiz_session_version`
  adds the version column.
- Student WebSocket authentication uses the `auth.<token>` subprotocol; the signed token is not
  included in the connection URL.
- WebSocket reconnect smoke passed against both SQLite and SQL Server; `quiz.ping` receives
  `quiz.ping.ack`, and reconnect snapshots advance the per-session sequence.
- Reconnect snapshots include the joined team at zero points before judging and the persisted
  awarded score after judging; the student scoreboard refreshes on judged-answer events.
- The production Docker image is configured to run the API as a non-root `app` user; the image
  build remains a CI check because the local Docker daemon is unavailable.
- The Next.js quiz page reads class tracks from `/api/v1/classes` through the configured same-origin FastAPI proxy; the verified response is IX/Python, X/C++, and XI/Python.
- The standard Next.js runtime now starts without a custom Socket.IO server; `/quiz` and the
  `/api/v1/classes` proxy returned HTTP 200 with database-backed data.
- The student join screen also reads team choices from `/api/v1/teams?class_code=IX`; through the Next proxy this returned the database-backed `Demo Team` record.
- FastAPI exposes signed admin login at `/api/v1/auth/login`, protected admin routes, `/api/v1/admin/audit-log`, and a native WebSocket snapshot at `/api/v1/ws/quiz/{session_id}`.
- The configured SQL Server database now contains question, quiz, participation, scoring, and audit tables in addition to the team foundation tables.
- When a database-backed quiz code is used, the student join flow resolves the FastAPI session and records the selected team as a quiz participant before entering the live room.
- `backend/scripts/e2e_smoke.py` completed the full disposable flow locally and returned a 10-point
  leaderboard result with WebSocket snapshot and idempotent judging replay verified.
- The same smoke completed against a fresh SQLite database, which verifies that token-derived UUID
  identifiers are normalized before database writes and that the end-to-end contract is not relying
  on SQL Server's permissive coercion behavior.
- The student join screen fails closed when class or team configuration cannot be loaded; it does
  not substitute editorial/static teams for database-backed event data. Room lookup and join errors
  remain visible and reset the joining state for retry.
- Signed authentication tokens with malformed payloads, invalid expiry types, invalid base64, or
  invalid signatures are rejected without raising server errors; the regression suite covers this
  boundary.

## Current connection map

1. The browser talks to the standard Next.js application and same-origin `/api/v1/*` rewrites.
2. The student room transport uses the FastAPI WebSocket and persisted buzzer/answer state.
3. FastAPI is a separately runnable service under `backend/`; it now exposes health, authentication, class/team reads, question authoring, quiz blueprints, quiz sessions, participation, scoring, leaderboards, audit logs, and a WebSocket snapshot endpoint.
4. FastAPI now uses the local SQL Server Express `UNKNOWN` database through ODBC Driver 18 and Windows Shared Memory; SQLite remains available for isolated fallback development.
5. The frontend uses FastAPI for class/team reads, question authoring, student room state, buzzer,
   answer submission, and the durable admin console.

## Known gaps before claiming end-to-end readiness

- Re-run the SQL Server backup/restore rehearsal in the production environment and retain the
  row-count and audit-continuity evidence with the release record.
- Run a production-style soak/load test with real event content and multiple teams before the
  event, including multi-worker rate-limit behavior.
- Verify secret-manager injection, alerting, and rotation procedures in the production environment.
The system is locally buildable and the frontend, FastAPI, and SQL Server are connected. FastAPI
realtime is now the only quiz transport; production-environment restore evidence, load/soak
testing, and operational secret/alert verification remain before production cutover.
