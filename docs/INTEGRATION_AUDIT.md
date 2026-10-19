# Integration Audit

Date: 2026-10-19

## Verified locally

| Boundary | Result | Evidence |
|---|---|---|
| Next.js frontend build | Pass | `npm run build` completes successfully |
| FastAPI liveness | Pass | `GET /health/live` returns HTTP 200 |
| FastAPI readiness | Pass on SQL Server Express | `GET /health/ready` returns HTTP 200 with `database: ok` |
| FastAPI OpenAPI | Pass | `/openapi.json` is generated |
| FastAPI tests | Pass | 16 tests pass |
| Alembic migration discovery | Pass | `0001_baseline_schema` is the current head |
| SQL Server connectivity | Pass locally | SQL Server Express `SQLEXPRESS`, ODBC Driver 18, database `UNKNOWN`, and the baseline migration are active |

## Current implementation evidence

- The backend now has 16 passing tests against the configured SQL Server database, covering authentication identity, question privacy, blueprint validation, session generation, public quiz-code lookup, participation, scoring, duplicate answers, and audit behavior.
- The Next.js quiz page reads class tracks from `/api/v1/classes` through the configured same-origin FastAPI proxy; the verified response is IX/Python, X/C++, and XI/Python.
- The custom Next.js/Socket.IO server now starts successfully through `tsx server.ts`; `/quiz` returned HTTP 200, the Socket.IO polling handshake returned HTTP 200, and the `/api/v1/classes` proxy returned database-backed class tracks.
- The student join screen also reads team choices from `/api/v1/teams?class_code=IX`; through the Next proxy this returned the database-backed `Demo Team` record.
- FastAPI exposes signed admin login at `/api/v1/auth/login`, protected admin routes, `/api/v1/admin/audit-log`, and a native WebSocket snapshot at `/api/v1/ws/quiz/{session_id}`.
- The configured SQL Server database now contains question, quiz, participation, scoring, and audit tables in addition to the team foundation tables.
- When a database-backed quiz code is used, the student join flow resolves the FastAPI session and records the selected team as a quiz participant before entering the live room.
- The scorecard import now populates 14 public teams (IX=5, X=6, XI=3) and 28 decimal-preserving score entries for the completed Round 0 and Round 1 results.

## Current connection map

1. The browser currently talks to the Next.js/Node application through the existing same-origin `/api/*` routes.
2. The live room transport still uses the existing Node Socket.IO server and in-memory room state, while FastAPI now records database-backed session participation and exposes a WebSocket snapshot endpoint.
3. FastAPI is a separately runnable service under `backend/`; it now exposes health, authentication, class/team reads, question authoring, quiz blueprints, quiz sessions, participation, scoring, leaderboards, audit logs, and a WebSocket snapshot endpoint.
4. FastAPI now uses the local SQL Server Express `UNKNOWN` database through ODBC Driver 18 and Windows Shared Memory; SQLite remains available for isolated fallback development.
5. The frontend has partial FastAPI cutover for class/team reads; the active quiz room and buzzer flow still uses the legacy Socket.IO path.

## Known gaps before claiming end-to-end readiness

- Move the frontend API client from the legacy Node routes to versioned FastAPI routes.
- Migrate realtime quiz delivery and admin monitoring from Socket.IO/in-memory state to a durable FastAPI-compatible design.
- Replace the current frontend Socket.IO room/buzzer flow with a durable FastAPI realtime controller and persist room state/events; the current page keeps Socket.IO for live buzzer compatibility after FastAPI participant registration.
- The legacy Socket.IO flow remains the active student room/buzzer path until the FastAPI WebSocket protocol is feature-complete and the frontend client is switched behind a controlled flag.
- Run the production-style end-to-end test with real event content and multiple teams before the event.

The system is locally buildable and the frontend, FastAPI, and SQL Server are connected. The remaining realtime transport is intentionally retained on the existing Socket.IO room controller while its durable FastAPI replacement is developed.
