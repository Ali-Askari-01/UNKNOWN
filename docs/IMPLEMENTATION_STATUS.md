# Implementation Status

## Phase 0 — Contract freeze

Implemented. The authority map and REST/realtime rules are recorded in
[PHASE0_CONTRACT_FREEZE.md](PHASE0_CONTRACT_FREEZE.md).

## Phase 1 — Repository and runtime baseline

Implemented and locally verified.

- Frontend TypeScript errors are no longer ignored by Next production builds.
- `pnpm typecheck` is available as an explicit check.
- `pnpm test:backend` runs the FastAPI test suite.
- `pnpm check` runs type checking, backend tests, and the production build.
- FastAPI startup requires `BACKEND_CORS_ORIGINS` in production and uses credentialed allowlisted
  CORS.
- GitHub Actions now runs frontend typecheck/build and backend lint/tests on pushes and pull
  requests.
- FastAPI admin login now issues an HttpOnly backend session cookie, and the admin UI uses only the
  versioned auth endpoints.
- Team join now validates the quiz code and class/team relationship, issues a scoped HttpOnly team
  cookie, and protects participant and answer mutations from arbitrary participant IDs.
- Durable quiz-session actions now persist `open`, `start`, `pause`, `resume`, `advance`, and `end`
  transitions with current-question timestamps and audit records; database row versions reject stale
  concurrent lifecycle writes.
- FastAPI realtime now requires an admin or session-scoped team token, sends a sanitized initial
  snapshot, supports ping/snapshot requests, and broadcasts lifecycle changes with sequenced event
  envelopes.
- Realtime snapshots now restore persisted buzzer state, winner/deadline, and scores; browser
  connections reconnect with bounded backoff, and sequence numbers advance across reconnects.
- Live score publication now refreshes the student scoreboard after judged-answer events, while
  reconnect snapshots include joined teams with zero or non-zero persisted scores.
- Buzzer presses are now persisted, scoped to the authenticated team, linked to the answer window,
  and protected by a one-winner-per-question database constraint.
- The student quiz uses the FastAPI WebSocket and durable buzzer endpoint after a successful
  database-backed join.
- Added a durable admin console at `/admin/durable-quiz` for persisted session creation,
  lifecycle control, answer judging, and a linked question bank. `/admin/quiz` now redirects to
  the durable console.
- Answer submission is now a pending workflow: staff can inspect the database-backed judging queue,
  approve or reject each answer, and only judged answers create score ledger entries.
- Production backend startup now rejects default authentication secrets, SQLite, and development
  admin bypass settings; trusted-host validation is enabled.
- The production Docker image now declares a liveness health check, and CI starts the built image
  with two workers to verify the entrypoint reaches `/health/live` without running migrations by
  default.
- The legacy Node/Socket.IO runtime, fallback flag, in-memory repositories, and compatibility API
  routes have been removed from the production application path.
- Backend admin authentication now requires `BACKEND_ADMIN_PASSWORD_HASH` (bcrypt) in production;
  the plaintext development credential is rejected outside development.
- Authentication, team join, buzzer, and answer mutations now use SQL-backed sliding-window limits
  with locked per-bucket coordination, so multiple API workers share the same abuse window.
- API requests now emit structured JSON logs with request ID, method, path, status, and duration;
  error envelopes include the request ID for operator correlation.
- Production/staging SQL Server workers now use bounded, configurable connection pools with
  pre-ping, timeout, overflow, and recycle controls; local/test SQL Server keeps `NullPool` to
  avoid event-loop-bound aioodbc connections.
- The production container now accepts bounded `BACKEND_WORKERS` (1–8) and applies a graceful
  shutdown timeout, enabling the planned multi-worker staging soak; the hosted default stays at one
  worker until that soak is approved.
- Production web containers no longer run Alembic automatically on startup; migrations require an
  explicit controlled operation through the separate migration runner identity.
- Production readiness now fails closed if the SQL-backed realtime relay is not running, and safe
  relay cursor/connection diagnostics are exposed through `/health/ready`.
- Release preflight now verifies every FastAPI-owned table and column while explicitly leaving
  unrelated legacy SQL Server objects untouched.
- API responses now include security headers; production adds HSTS and regression coverage verifies
  the development and production header sets.
- Production JavaScript dependency audit passes with no known moderate-or-higher advisories; the
  `shadcn` CLI is development-only and patched transitive versions are pinned centrally.

## Current verification

- FastAPI tests: 38 passed locally, including bcrypt authentication, malformed-token rejection, production-config rejection,
  and concurrent buzzer
  arbitration; Ruff checks pass.
- Frontend TypeScript check: passed with Next 16.4.0.
- Production build: passed with all landing, auth, quiz, durable admin, and class-track routes
  generated successfully.
- Runtime smoke: passed landing/admin/student HTTP checks, FastAPI readiness, authenticated
  session creation, lifecycle start, team join, buzzer, pending answer, judging, and leaderboard.
- Browser smoke: passed student WebSocket join/buzzer/answer flow and durable admin queue/judging
  flow against the running services.
- End-to-end smoke: passed admin login, session creation, open/start, team join, WebSocket snapshot,
  buzzer, answer submission, judging, idempotent replay, leaderboard publication, and session end
  through `backend/scripts/e2e_smoke.py` against the local SQL Server service.
- The checked-in smoke now verifies idempotent replay for session actions, team join, answer
  submission, and answer judging, matching the browser's retry-safe mutation contract.
- The smoke also verifies authenticated WebSocket ping acknowledgements and reconnect snapshots with
  advancing sequence numbers against both SQLite and SQL Server.
- Clean-database portability smoke: passed the same end-to-end flow against a disposable SQLite
  service, including UUID-scoped team authentication and buzzer/answer writes.
- SQL Server restore rehearsal: passed backup verification, restore to a separate database, Alembic
  revision check, matching source/restored row counts, and `/health/ready` against the restored DB.
- Load smoke: passed five authenticated teams racing the same active question with exactly one
  `201` winner and four controlled `409` conflicts.
- Bounded soak smoke: passed two concurrent end-to-end sessions against both fresh SQLite and
  local SQL Server; every iteration verified reconnect snapshots and score publication.
- Two-worker SQLite startup and E2E smoke: passed after adding cross-process initialization locking;
  CI now runs its service with two workers.
- Multi-worker smoke: passed the same five-team winner race through two FastAPI workers against
  SQL Server with exactly one `201` winner and four `409` conflicts.
- Release preflight: passed locally against SQL Server at Alembic head
  `0009_question_content_snapshots`, including database connectivity and the FastAPI-owned schema
  contract.
  The current release adds `0010_auto_quiz_rules`; the connected SQL Server must be migrated to
  that head before the automatic grading fields can be used there.
  strict production mode rejects incomplete/default configuration without printing secret values.
- Production-configured runtime smoke: `/health/ready` returned HTTP 200 against SQL Server with
  `database: ok`, migration validation, and `realtime.relayRunning: true`.
- Production readiness now fails closed when the database schema revision is missing or older than
  the application release head.
- WebSocket authentication now carries the signed token in a negotiated subprotocol instead of a
  URL query string, reducing token exposure in proxy/access logs.
- Realtime broadcasts are persisted in SQL Server and relayed by each worker's polling loop, so
  WebSocket clients connected to different API workers receive the same committed event stream.
- Question-bank admin surface: `/admin/questions` now lists and creates database-backed questions
  through the versioned FastAPI API, with class-track selection and MCQ validation.
- Full production readiness: not yet claimed; production load testing, secret-manager deployment,
  and production-environment operational verification remain before final cutover. The restore rehearsal is locally
  proven; production scheduling and evidence retention still require the deployment owner.
