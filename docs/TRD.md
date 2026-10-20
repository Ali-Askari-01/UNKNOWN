# UNKNOWN / TLC Technology Competition — Technical Requirements Document

Version: 1.0  
Target backend: FastAPI  
Target database: Microsoft SQL Server  
Frontend: existing Next.js App Router application

## 1. Target architecture

```text
Browser
  ├── HTTPS/JSON ───────► FastAPI REST API
  └── Native WebSocket ► FastAPI realtime gateway
                              │
                              ├── Application services
                              ├── Authorization/policy layer
                              ├── SQLAlchemy repositories
                              ├── SQL Server
                              └── Object storage for media
```

FastAPI is the only authority for mutations. Next.js remains responsible for page rendering and
browser UX. The former TypeScript/Socket.IO server has been retired after endpoint and realtime
parity was proven.

## 2. Recommended Python stack

- Python 3.12 or the team’s approved current Python LTS-compatible version.
- FastAPI with Pydantic v2 schemas.
- SQLAlchemy 2.x ORM/core.
- SQL Server through `mssql+aioodbc` for async request paths, with ODBC Driver 18 configured securely; use synchronous tooling only where migration tooling requires it.
- Alembic for versioned migrations.
- `python-jose`/PyJWT only if the team selects a standard JWT flow; otherwise use signed opaque tokens with server-side revocation.
- Argon2id or bcrypt for passwords; never store plaintext credentials.
- `pytest`, `pytest-asyncio`, and HTTPX test clients.
- Structured logging, OpenTelemetry-compatible tracing, and health/readiness endpoints.

The SQLAlchemy SQL Server dialect documents both `pyodbc` and `aioodbc` options, including async engine usage. FastAPI deployment must account for HTTPS, startup, restarts, replication, memory, and pre-start checks; these are explicit deployment requirements, not afterthoughts.

## 3. Service boundaries

| Module | Responsibility |
|---|---|
| `identity` | Admin login, team tokens, roles, sessions, revocation |
| `events` | Editions, classes, rounds, schedule, announcements |
| `teams` | Students, memberships, team profiles, media links |
| `questions` | Question bank, options, tags, eligibility, moderation |
| `quizzes` | Blueprint validation, session lifecycle, question selection |
| `realtime` | Connections, room membership, buzzer events, broadcasts |
| `answers` | Submission, judging, timeout, answer-key protection |
| `scoring` | Append-only score ledger and leaderboard projections |
| `submissions` | Posters, projects, presentations, evaluation criteria |
| `audit` | Structured audit events and administrative history |

Each service depends on repository interfaces and policy interfaces, not on SQLAlchemy models directly. Transactions are owned by the application-service boundary.

## 4. API and realtime requirements

- Version REST routes under `/api/v1`.
- Return a consistent error envelope with request ID, error code, message, and field errors.
- Validate all request bodies, query parameters, path values, and websocket payloads.
- Use idempotency keys for score publication, submission creation, and other retry-sensitive writes.
- Use optimistic concurrency/version checks for admin edits.
- Use server-generated UTC timestamps.
- Do not expose answer keys, private student fields, storage keys, or audit details to public clients.
- Use a single event schema for websocket messages; include event ID, server timestamp, room/session ID, and sequence number.

## 5. Database requirements

- SQL Server schema is `competition` and is created by Alembic/SQL migration steps.
- Migrations are forward-only in production; rollback scripts are prepared for risky releases.
- Application database account has only required schema permissions.
- Foreign keys, unique constraints, check constraints, filtered indexes, and transaction boundaries are mandatory.
- Score history and audit history are append-only by application policy.
- Historical quiz question snapshots are immutable after session start.
- Media binaries are external; SQL Server stores metadata and object keys.

## 6. Deployment requirements

- Separate development, staging, and production configurations.
- Container image or reproducible process definition for FastAPI.
- Reverse proxy/managed ingress terminates HTTPS and forwards trusted headers.
- WebSocket connection state is process-local, while committed events are relayed through the
  SQL-backed realtime event ledger. Production horizontal scaling still requires the documented
  multi-worker soak. API rate-limit state also uses a shared SQL store when multiple workers are
  deployed.
- Readiness must fail if required secrets or database connectivity are unavailable.
- Logs must not contain passwords, tokens, answer keys, or student private data.

## 7. Definition of technical completion

- FastAPI serves all required REST endpoints and realtime events.
- SQL Server persistence survives restart and passes migration/restore tests.
- Existing frontend works through the new API without business-rule duplication.
- Buzzer race, scoring transaction, permissions, and audit tests pass.
- Production build/runbook/monitoring documentation is complete.
