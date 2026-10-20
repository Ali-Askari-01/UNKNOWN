# UNKNOWN — Quiz Competition Platform

Production-bound quiz competition platform for Classes IX, X, and XI. Administrators create and
operate database-backed quiz sessions; student teams join with a quiz code, compete through a
durable buzzer flow, submit answers, and receive judged scores.

## Runtime architecture

- Next.js 16 + React 19 + strict TypeScript frontend.
- FastAPI versioned API and native WebSocket realtime service in `backend/`.
- SQL Server is the production system of record; SQLite is used only for isolated development.
- Alembic migrations are stored in `backend/migrations/`.
- The browser uses `/api/v1/*` same-origin rewrites and `NEXT_PUBLIC_FASTAPI_WS_URL` for realtime.
- The former Node/Socket.IO server, in-memory repositories, and compatibility API routes have been
  removed from the application runtime.

## Local setup

Prerequisites: Node.js 22+, pnpm 12+, Python 3.12+, and the backend dependencies.

```powershell
pnpm install
Copy-Item .env.example .env.local
Push-Location backend
python -m pip install -e ".[dev]"
Pop-Location
```

Configure `backend/.env` for SQLite development or SQL Server integration. Production must provide
`BACKEND_DATABASE_URL`, `BACKEND_AUTH_SECRET`, `BACKEND_ADMIN_PASSWORD_HASH`, trusted hosts, and
an explicit CORS allowlist through the deployment secret manager.

Run the services in separate terminals:

```powershell
Push-Location backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Pop-Location

pnpm dev
```

The frontend is available at `http://localhost:3000`.

## Main surfaces

- `/` — public landing page.
- `/quiz` — student class, room-code, team join, buzzer, and answer flow.
- `/admin/login` — FastAPI-backed administrator login.
- `/admin/questions` — authenticated database-backed question bank.
- `/admin/durable-quiz` — persisted session lifecycle and answer judging.
- `/dashboard/class/[classId]` — public class/team track view.

## Verification

```powershell
corepack pnpm check
```

The check runs frontend typechecking, backend Ruff/tests, and the production build. Additional
runtime, backup/restore, load-smoke, security, and release evidence is documented in:

- [Implementation status](docs/IMPLEMENTATION_STATUS.md)
- [Integration audit](docs/INTEGRATION_AUDIT.md)
- [Production release runbook](docs/PRODUCTION_RELEASE_RUNBOOK.md)
- [FastAPI API contract](docs/FASTAPI_API_CONTRACT.md)
- [FastAPI security requirements](docs/FASTAPI_SECURITY.md)
- [Phase 0 contract freeze](docs/PHASE0_CONTRACT_FREEZE.md)

## Current release status

The frontend, FastAPI service, SQL Server schema, authentication, durable realtime, question bank,
scoring, restore rehearsal, and concurrency smoke tests are connected and locally verified. Final
production cutover still requires production-environment restore evidence, a realistic multi-worker
load/soak test, secret-manager verification, and operational sign-off.
