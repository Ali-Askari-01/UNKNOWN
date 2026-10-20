# API Documentation

The browser-facing API is versioned under `/api/v1`. Next.js rewrites these requests to the
FastAPI service at `FASTAPI_INTERNAL_URL`; FastAPI and SQL Server own validation, authorization,
transactions, and persistence.

## Health and discovery

- `GET /health/live` — process liveness.
- `GET /health/ready` — database-backed readiness; production also requires the expected Alembic
  migration head and a running SQL-backed realtime relay. The response includes safe relay status
  and event cursor diagnostics.
- `GET /api/v1/classes` — public class tracks.
- `GET /api/v1/teams?class_code=IX` — public teams and approved members for a class.

## Authentication

- `POST /api/v1/auth/login` — admin login; sets the HttpOnly `unknown_admin_session` cookie and
  returns a bearer token.
- `POST /api/v1/auth/team/join` — validates quiz code/team/session and issues a scoped team token;
  accepts `Idempotency-Key` for safe browser retries.
- `GET /api/v1/auth/me` — current admin authentication status.
- `POST /api/v1/auth/logout` — clears the admin and team cookies.

## Question bank and quiz setup

- `GET /api/v1/questions` — public questions without answer keys.
- `GET /api/v1/admin/questions` — staff question bank with answer keys.
- `POST /api/v1/admin/questions` — create a validated question and class-track assignment.
- `GET /api/v1/quiz-blueprints` — public blueprint metadata.
- `GET /api/v1/admin/quiz-blueprints` — staff blueprint list.
- `POST /api/v1/admin/quiz-blueprints` — create a validated blueprint.

## Quiz sessions

- `POST /api/v1/admin/quiz-sessions` — create a persisted session from a blueprint.
- `GET /api/v1/admin/quiz-sessions` — list persisted sessions.
- `GET /api/v1/quiz-sessions/by-code/{quiz_code}` — resolve a public join code.
- `POST /api/v1/admin/quiz-sessions/{id}/actions/{open|start|pause|resume|advance|end}` — apply a
  validated lifecycle transition; accepts `Idempotency-Key` for safe admin retries.
- `GET /api/v1/quiz-sessions/{id}/questions` — currently open public question only.
- `GET /api/v1/admin/quiz-sessions/{id}/questions` — staff question snapshot including answer key.

## Participation and scoring

- `POST /api/v1/quiz-sessions/{session_id}/questions/{question_id}/buzzer` — scoped team buzzer;
  exactly one winner is committed by the database.
- `POST /api/v1/quiz-sessions/{session_id}/answers` — winning team submits a pending answer;
  accepts `Idempotency-Key` for safe browser retries.
- `GET /api/v1/admin/quiz-sessions/{session_id}/answers` — staff judging queue.
- `POST /api/v1/admin/quiz-sessions/{session_id}/answers/{answer_id}/judge` — judge once and write
  the score ledger entry.
- `GET /api/v1/quiz-sessions/{session_id}/leaderboard` — persisted leaderboard projection.
- `GET /api/v1/admin/audit-log` — administrative audit history.

## Realtime

Connect to `/api/v1/ws/quiz/{session_id}` with the signed token in the negotiated
`Sec-WebSocket-Protocol: auth.<token>` header. See [REALTIME_EVENTS.md](REALTIME_EVENTS.md) for
the event envelope and client intents.

All former unversioned `/api/*` compatibility routes have been removed to prevent a second,
in-memory authority from being used accidentally.
