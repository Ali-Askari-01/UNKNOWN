# Testing

> Status: Phase 2 plan. Test infrastructure lands in Phase 9 (Vitest).

## Tooling (planned)

- **Vitest** as the test runner (fast, TS-native, works with pnpm).
- `tests/unit/` — services, validation schemas, session tokens.
- `tests/integration/` — repository + service wiring, socket event flows against an
  in-memory Socket.IO server.
- Scripts (to be added): `pnpm test`, `pnpm test:watch`, `pnpm test:coverage`.

No tests exist in the repository yet.

## What Will Be Covered

### Unit
- Zod schemas: accept valid payloads, reject unknown/oversized/missing fields.
- `ScoringService`: award, deduct, manual adjust, tiebreak ordering.
- `BuzzerService`:
  - first press wins; second press rejected;
  - press after expiry rejected; press by already-buzzed team rejected;
  - 20s window fires exactly once (fake timers);
  - reopen excludes already-buzzed teams.
- `QuizService` lifecycle: invalid transitions (e.g. start→start) return 409-equivalent
  errors; pause cancels timers.
- Session tokens: create/verify round-trip; tampered signature rejected;
  expired token rejected.

### Integration
- Simultaneous buzzer presses: fire N parallel `buzzer:press` events through the real
  Socket.IO server; assert **exactly one** ack `{ ok: true }` and one winner.
- Admin permission matrix: every `admin:*` event with a non-admin socket → forbidden;
  with admin socket → ok.
- Join flow: wrong code, unknown group, valid join, rotate code → old code fails.
- Leaderboard: sequence of correct/incorrect/adjust events → expected ranking.

### Build
- `pnpm build` (production `next build`) must pass in CI before merge.

## Conventions

- No real timers in tests — use Vitest fake timers for the 20s window.
- In-memory repositories are constructed fresh per test (no shared global state).
- Tests never depend on a database (there is none) or network access.
- Socket tests bind to port `0` (ephemeral) to avoid clashes.

## Known Non-Goals (this phase)

- No browser E2E (Playwright/Cypress) yet.
- No load testing; single-process in-memory design is not horizontally scalable.
