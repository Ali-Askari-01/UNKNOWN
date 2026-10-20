# Testing and Verification

## Automated gate

```powershell
corepack pnpm check
```

This runs strict frontend TypeScript validation, frontend Vitest unit tests, FastAPI Ruff/tests,
and the production Next.js build. Frontend-only checks are available with `pnpm test:frontend`;
backend-only checks are available with `python -m ruff check app tests scripts migrations` and
`python -m pytest -q` from `backend/`.

CI also runs `pnpm audit --prod --audit-level moderate`; the production dependency graph is kept
free of known moderate-or-higher advisories through workspace-level patched-version overrides.

CI also builds the production FastAPI Docker image so the Render deployment artifact is checked,
including the explicit migration-disabled-by-default entrypoint, and starts that image with two
workers to verify the container liveness endpoint and process lifecycle.
CI also renders the complete Alembic chain in offline mode, which validates every revision without
requiring a SQL Server service in the test runner.
CI also starts a clean SQLite FastAPI process and runs the full E2E smoke against it, covering
authentication, lifecycle, join, realtime authentication, ping/pong, reconnect snapshots, answer
judging, idempotency, and leaderboard output.
CI also runs a bounded two-iteration, two-concurrent-session soak against a two-worker SQLite
service using
`backend/scripts/quiz_soak_smoke.py`.

## Coverage expectations

- Authentication identity, bcrypt verification, production configuration rejection, and logout.
- Public question privacy and authorized admin answer-key access.
- Blueprint and quiz-session lifecycle transitions.
- Team/session ownership, pending answers, judging, score ledger, and audit records.
- Concurrent buzzer presses with exactly one database-confirmed winner.
- Frontend realtime client behavior via Vitest: endpoint URL construction, encoded session paths,
  subprotocol token authentication, exponential reconnect backoff with cap and reset, explicit-close
  cancellation, and malformed event tolerance.
- Question creation rejects invalid class-track references.
- SQL Server readiness, migration state, backup verification, and restore rehearsal.
- Five-team authenticated load smoke against one active question.
- Browser/runtime smoke for landing, admin login, question bank, student join, WebSocket,
  buzzer, answer submission, judging, and leaderboard.
- The checked-in `backend/scripts/e2e_smoke.py` reproduces the disposable end-to-end flow and
  verifies WebSocket snapshots, idempotent judging replay, and leaderboard publication.
- The checked-in `backend/scripts/quiz_soak_smoke.py` repeats the complete flow with bounded
  concurrency and reports duration plus reconnect/score-publication invariants.

## Release-only checks

Before cutover, repeat the smoke and load tests against the production-like deployment with real
event content, multiple API workers, shared rate-limit state, secret-manager injection, monitoring,
and the documented rollback/restore procedure.
