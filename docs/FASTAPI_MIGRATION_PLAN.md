# FastAPI Backend Migration Plan

## Strategy

Use a strangler migration. Build FastAPI beside the existing Node backend, preserve public behavior through compatibility routes, move one capability at a time, and remove the Node server only after parity and recovery tests pass.

## Phase 0 — contract freeze

- Inventory every frontend fetch and Socket.IO event.
- Freeze current request/response/event fixtures.
- Define `/api/v1` contracts and error envelope.
- Decide cookie/token compatibility and API origin configuration.

Exit criteria: contract fixtures are committed and reviewed.

## Phase 1 — FastAPI skeleton

- Add `backend/` package, settings, logging, request ID middleware, health/readiness, CORS, exception handlers, and dependency injection.
- Add SQLAlchemy engine/session factory and migration configuration.
- Add CI for Python format/lint/type checks and unit tests.

Exit criteria: FastAPI starts, `/health/live` works, `/health/ready` checks SQL Server.

## Phase 2 — shared domain and read-only parity

- Implement class, team, question, and leaderboard read endpoints.
- Map SQL models to response schemas without leaking private fields.
- Keep legacy Node endpoints active.
- Compare FastAPI and Node response projections in staging.

Exit criteria: read-only contract tests and frontend shadow traffic match.

## Phase 3 — identity and CRUD writes

- Implement admin login/session, roles, team/student CRUD, question CRUD/import, and audit logging.
- Add idempotency and optimistic concurrency.
- Point admin write screens to FastAPI using a feature flag.

Exit criteria: staff workflows pass with SQL persistence and audit records.

## Phase 4 — quiz lifecycle and scoring

- Implement blueprint validation and randomized question selection.
- Implement session lifecycle, team join, answer submission, judging, and score ledger.
- Run Node and FastAPI against separate staging data and compare outcomes.

Exit criteria: complete quiz run is durable and scores match reference behavior.

## Phase 5 — realtime cutover

- Implement websocket event envelope, authentication, rooms, snapshots, sequence numbers, reconnect, and buzzer transactions.
- Run simultaneous-buzzer, timeout, reconnect, and multi-tab tests.
- Keep Node realtime as rollback path during a pilot.

Exit criteria: no duplicate winners; all clients converge on the same session snapshot.

## Phase 6 — frontend cutover

- Replace legacy API base URL and socket client with FastAPI adapters.
- Retain compatibility fallback only for staging/rollback.
- Monitor errors, latency, reconnects, and score discrepancies.

Exit criteria: frontend has no runtime dependency on the Node server.

## Phase 7 — retire and harden

- Freeze Node endpoint changes.
- Archive compatibility code after the agreed observation window.
- Remove old server only after backup/restore and rollback rehearsal.
- Add public showcase/media, exports, reports, and next-edition tooling.

Exit criteria: FastAPI is the only production backend and operational ownership is documented.
