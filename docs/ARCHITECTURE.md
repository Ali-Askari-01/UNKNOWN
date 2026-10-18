# Architecture

> Status: Phase 2 design. Implementation lands in Phases 3–8.
> Current runtime (pre-refactor): `server.ts` + `lib/quiz-state.ts` own all state; see
> "Current Runtime" at the bottom.

## Design Goals

1. No database in this phase — in-memory repositories behind interfaces.
2. Business logic (services) fully separated from storage (repositories) so a persistent
   repository can replace the in-memory one later without touching services or APIs.
3. Server-authoritative quiz logic: timers, buzzer winner selection, and scoring are
   decided only on the server.
4. Existing UI files are adapted, not rewritten.

## Proposed Folder Structure

Existing directories (`app/`, `lib/`, `components/`, `data/`, `public/`) stay at the repo
root (the `@/*` alias maps to `./*`). New backend code is added alongside them:

```
app/
  api/                          # Next.js Route Handlers (HTTP API)
    admin/                      #   existing: login, logout, me
    classes/                    #   class tracks CRUD (Phase 5)
    teams/                      #   team management (Phase 5)
    questions/                  #   question bank (Phase 5)
    quizzes/                    #   quiz lifecycle + codes (Phase 5)
    join/                       #   student join endpoint (Phase 5)
    answer/                     #   answer submission (Phase 7)
    leaderboard/                #   score query (Phase 7)
lib/
  auth/                         # session tokens, guards, password hashing (Phase 4)
  validation/                   # Zod schemas for every API/socket payload (Phase 3)
  session.ts                    # existing HMAC session util (kept, moved logic to lib/auth)
  socket-client.ts              # existing browser socket singleton (unchanged)
  utils.ts                      # existing cn() helper (unchanged)
server/
  services/                     # business logic (Phases 3, 6, 7)
    quiz-service.ts             #   lifecycle: open/start/pause/resume/finish, question flow
    buzzer-service.ts           #   activate/press/timeout/reopen, atomic first-winner
    scoring-service.ts          #   award/deduct, score calculation
    team-service.ts             #   class + team CRUD rules
    question-service.ts         #   question CRUD rules
    leaderboard-service.ts      #   ranking projection
  repositories/                 # storage interfaces + in-memory implementations (Phase 3)
    types.ts                    #   repository interfaces (TeamRepo, QuestionRepo, …)
    in-memory/                  #   Map-backed implementations
  realtime/                     # Socket.IO wiring (Phase 6)
    socket-server.ts            #   server construction, auth middleware
    handlers/                   #   one module per event family (room, buzzer, admin, quiz)
types/
  index.ts                      # shared domain + API types (Phase 3)
tests/                          # Vitest (Phase 9)
  unit/  integration/
docs/                           # this folder
```

`lib/quiz-state.ts` logic is **migrated** into services/repositories (not duplicated);
the file is removed or reduced to a compatibility shim once the frontend is wired in
Phase 8.

## Service Boundaries

| Service | Responsibility | Depends on |
|---|---|---|
| `TeamService` | Class/team CRUD, membership rules | `TeamRepository` |
| `QuestionService` | Question CRUD, per-class ordering | `QuestionRepository` |
| `QuizService` | Quiz lifecycle, current question pointer, joining rules, room codes | `QuizRepository`, `RoomRepository`, `QuestionService`, `BuzzerService`, `ScoringService` |
| `BuzzerService` | Buzzer open/lock/expiry, atomic first-winner selection, 20s answer window, timeout + reopen | `RoomRepository` (timer handles kept in memory) |
| `ScoringService` | Award/deduct points, recompute team totals | `QuizRepository` |
| `LeaderboardService` | Sorted ranking projection for a class | `ScoringService` data |

Services never import from `server/repositories/in-memory/*` directly — only from the
interfaces in `server/repositories/types.ts`. The composition root (a small
`server/container.ts`) binds in-memory implementations for now.

## Data Flow

```
Browser (admin) ──HTTP──► Route Handler ──► Zod validation ──► Service ──► Repository
Browser (student) ──WS───► Socket handler ──► Zod validation ──► Service ──► Repository
                                   ▲                                  │
                                   └──── broadcast room:state ◄──────┘
```

- HTTP is used for CRUD, login, join, and anything that must work without a socket.
- Socket.IO carries live quiz control and buzzer traffic; every mutation still goes
  through the same service layer, then broadcasts `room:state` snapshots.

## Authentication Design

### Admin
- Single account from env: `ADMIN_USERNAME` + `ADMIN_PASSWORD_HASH` (bcrypt).
- On login, server issues an HMAC-SHA256 signed session token in an HttpOnly,
  SameSite=Lax cookie (`quiz_admin_session`, 8h expiry).
- Enforcement layers:
  1. `proxy.ts` (Edge) — cheap cookie-presence gate for `/admin/*` and `/api/admin/*`.
  2. Route handlers — full signature verification on every admin API.
  3. Socket.IO middleware — `socket.data.role = 'admin'` set from handshake cookie;
     every `admin:*` event checks it server-side.
- Hardening vs current code: constant-time signature compare, refuse to start in
  production without `SESSION_SECRET`, restricted Socket.IO CORS origin.

### Student (Phase 5)
- Students are **teams**, not user accounts. On successful join
  (`classId` + valid quiz code + known group name), the server issues a short-lived
  team-scoped signed token (same HMAC scheme, distinct cookie/localStorage key).
- Socket handshake carries the team token; `socket.data.team` identifies the caller.
  Students can only press the buzzer / submit answers for their own team.
- The quiz code is a shared secret per room, rotated by the admin; it is not a
  credential by itself once a team holds a token.

## Real-time Architecture

- Single Socket.IO server attached to the existing custom HTTP server (`server.ts`).
- Rooms: `room:{classId}` for participants, `admin` for the admin panel.
- All authority lives server-side:
  - Buzzer winner: first accepted `buzzer:press` per question is stored atomically in
    the service; later presses are rejected. Simultaneous presses are serialized by
    Node's single-threaded event loop — the first event handler to commit wins.
  - Timers: `setTimeout` on the server marks answers expired at T+20s and broadcasts
    `buzzer:expired`; clients never run authoritative clocks (they only render a
    countdown from the server-provided `answerDeadline`).
- Snapshot model: after every mutation the server emits `room:state` with a full
  sanitized snapshot; clients are stateless renderers.

See `docs/REALTIME_EVENTS.md` for the event catalog and `docs/QUIZ_FLOW.md` for the
end-to-end round sequence.

## Current Runtime (as audited in Phase 1)

- `server.ts` — custom Next + Socket.IO server; all event handlers inline.
- `lib/quiz-state.ts` — singleton in-memory state machine, 3 hardcoded rooms
  (`IX2026`, `X2026`, `XI2026`), scores seeded from `data/event.ts` groups.
- `proxy.ts` — Edge cookie-presence gate.
- `lib/session.ts` — HMAC session tokens.

This runtime keeps working during Phases 3–7; the refactor lands in Phase 8 when the
frontend is rewired to the new service-backed handlers.
