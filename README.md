# UNKNOWN — Quiz Competition Platform

Live buzzer-style quiz competition site for Classes IX, X, and XI. One admin runs the
event; student teams join with a quiz code and compete in real time.

> **No database in this phase.** All state is in-memory and **resets on every server
> restart**. This is development persistence only — not production-grade storage.
> A repository interface is in place so a real database can be added later without
> rewriting business logic.

## Tech Stack

- Next.js 16 (App Router) + React 19 + TypeScript (strict)
- Custom Node server (`server.ts`) hosting Next.js + Socket.IO on one port
- Tailwind CSS 4, shadcn-style UI, pnpm
- Planned additions: Zod (validation), Vitest (tests)

## Getting Started

### Prerequisites
- Node.js 20+
- [pnpm](https://pnpm.io) 12+

### Install

```bash
pnpm install
```

### Environment

Copy the placeholder file and fill in real values locally (never commit them):

```bash
cp .env.example .env.local
```

| Variable | Purpose |
|---|---|
| `SESSION_SECRET` | HMAC key for admin session cookies — **required in production** |
| `ADMIN_USERNAME` | Admin login username (default `admin`) |
| `ADMIN_PASSWORD_HASH` | bcrypt hash of the admin password — login fails (503) if unset |
| `PORT` / `HOSTNAME` | Server bind (default `3000` / `localhost`) |
| `CORS_ORIGIN` | Planned: allowed origin for credentialed Socket.IO handshakes |

Generate the bcrypt hash (base64-encoded — Next.js env loading mangles raw `$` characters):

```bash
node -e "console.log('base64:' + Buffer.from(require('bcryptjs').hashSync('your-password', 10)).toString('base64'))"
```

### Run

```bash
pnpm dev        # custom server (Next + Socket.IO) on http://localhost:3000
pnpm build      # production build
pnpm start      # production server (Windows: set NODE_ENV=production first)
```

Pages:
- `/` — landing
- `/quiz` — student portal (join + buzzer)
- `/admin/login` — admin login
- `/admin/quiz` — admin control panel

## Architecture

```
app/api/              Route Handlers (HTTP API)
lib/auth/             Session tokens, guards          (Phase 4)
lib/validation/       Zod schemas                     (Phase 3)
server/services/      Business logic                  (Phases 3, 6, 7)
server/repositories/  In-memory storage behind        (Phase 3)
                      interfaces
server/realtime/      Socket.IO server + handlers     (Phase 6)
types/                Shared domain types             (Phase 3)
tests/                Vitest suites                   (Phase 9)
docs/                 Full documentation set
```

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Documentation

| Doc | Contents |
|---|---|
| [PROJECT_DESCRIPTION.md](docs/PROJECT_DESCRIPTION.md) | Product scope, panels, rules |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Folder structure, services, auth, realtime design |
| [API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) | HTTP API contracts |
| [QUIZ_FLOW.md](docs/QUIZ_FLOW.md) | Lifecycle, buzzer/answer flow, timing |
| [REALTIME_EVENTS.md](docs/REALTIME_EVENTS.md) | Socket.IO event catalog |
| [SECURITY.md](docs/SECURITY.md) | Auth, secrets, known gaps |
| [TESTING.md](docs/TESTING.md) | Test strategy (Vitest, planned) |
| [DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md) | Requirements, ERD, SQL Server recommendation, and migration plan |
| [PRD.md](docs/PRD.md) | Product requirements, roles, workflows, and success criteria |
| [TRD.md](docs/TRD.md) | FastAPI, SQL Server, security, deployment, and technical requirements |
| [DATABASE_REQUIREMENTS.md](docs/DATABASE_REQUIREMENTS.md) | Data ownership, integrity, transactions, and retention |
| [DATABASE_DATA_DICTIONARY.md](docs/DATABASE_DATA_DICTIONARY.md) | Entity purpose, fields, and derived views |
| [DATABASE_MIGRATION_AND_SEEDING.md](docs/DATABASE_MIGRATION_AND_SEEDING.md) | Migration, import, rollback, and environments |
| [DATABASE_SECURITY_OPERATIONS.md](docs/DATABASE_SECURITY_OPERATIONS.md) | Access, privacy, backups, monitoring, and operations |
| [DATABASE_TESTING.md](docs/DATABASE_TESTING.md) | Database correctness, quality, and performance tests |
| [FASTAPI_ARCHITECTURE.md](docs/FASTAPI_ARCHITECTURE.md) | Target Python backend structure and boundaries |
| [FASTAPI_API_CONTRACT.md](docs/FASTAPI_API_CONTRACT.md) | Versioned REST contract and compatibility strategy |
| [FASTAPI_REALTIME_AND_AUTH.md](docs/FASTAPI_REALTIME_AND_AUTH.md) | Tokens, websocket events, reconnects, and buzzer correctness |
| [FASTAPI_SECURITY.md](docs/FASTAPI_SECURITY.md) | FastAPI threat model and security controls |
| [FASTAPI_TESTING_DEPLOYMENT.md](docs/FASTAPI_TESTING_DEPLOYMENT.md) | Test layers, deployment, CI, and release checklist |
| [DATABASE_IMPLEMENTATION_PLAN.md](docs/DATABASE_IMPLEMENTATION_PLAN.md) | Phase-by-phase SQL Server implementation |
| [FASTAPI_MIGRATION_PLAN.md](docs/FASTAPI_MIGRATION_PLAN.md) | Phase-by-phase backend migration |
| [IMPLEMENTATION_ROADMAP.md](docs/IMPLEMENTATION_ROADMAP.md) | Master sequencing, gates, and missing decisions |

The first relational schema baseline is stored at
[`database/sqlserver/001_initial_schema.sql`](database/sqlserver/001_initial_schema.sql).

## API Quick Test

```bash
# Login (set ADMIN_PASSWORD_HASH in .env.local first)
curl -i -X POST http://localhost:3000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'

# Session check (use the cookie from the login response)
curl -i http://localhost:3000/api/admin/me -H "Cookie: quiz_admin_session=..."

# Logout
curl -i -X POST http://localhost:3000/api/admin/logout
```

Student/class/team/quiz endpoints are documented in
[docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) and land in Phases 5–7.

## Current Status

Backend build-out is phased:

- **Phase 1** — repository audit ✅
- **Phase 2** — architecture, API contracts, docs skeleton ✅ (this commit)
- **Phases 3–7** — validation, repositories, services, auth, APIs, realtime, scoring
- **Phase 8** — wire existing frontend to the new services
- **Phase 9** — Vitest suites (incl. simultaneous-buzzer and permission tests)
- **Phase 10** — final docs + limitation review

Working today: admin login/logout/session, in-memory quiz rooms, buzzer + 20s timer,
basic scoring — all via the original `server.ts` implementation.

## Known Limitations

- **No persistence** — all state (scores, questions, quiz status, joined teams) is
  lost on server restart.
- **Single process** — do not run multiple replicas; state is not shared.
- Socket.IO CORS is currently `origin: '*'` (hardening planned, see SECURITY.md).
- Admin login requires `.env.local` with a bcrypt hash; there is no default password.
- `pnpm start` uses Windows `set` syntax; adjust for other platforms.
- Type errors do not fail builds (`ignoreBuildErrors` in `next.config.mjs`).
