# Phase 0 — Contract Freeze

Status: implemented as the starting contract baseline.

This document records the integration boundary now enforced by the implementation. FastAPI is the
authority for all durable mutations and realtime quiz state; Next.js owns rendering and proxying.

## Authorities

| Concern | Production authority | Current migration status |
|---|---|---|
| Public event data | FastAPI + SQL Server | Landing content is intentionally editorial/static |
| Admin authentication | FastAPI session | Cut over and verified |
| Teams and classes | FastAPI + SQL Server | Cut over and verified |
| Question bank | FastAPI + SQL Server | Admin frontend cut over and verified |
| Quiz session lifecycle | FastAPI + SQL Server | Persisted transitions verified |
| Buzzer arbitration | FastAPI transaction/realtime gateway | Database winner constraint verified |
| Answer judging and scores | FastAPI ledger | Pending/judged workflow verified |
| Realtime snapshots | FastAPI WebSocket | Snapshot, lifecycle, buzzer, answer events verified |

## Required REST conventions

- Base path: `/api/v1`.
- State-changing requests must be authenticated and authorized server-side.
- Retry-sensitive creates and mutations must accept an idempotency key. The current release
  implements durable replay for team join, answer submission, answer judging, and admin session
  actions. New retryable mutation clients must adopt the same contract before being enabled.
- Responses must never expose answer keys to student/team clients.
- Errors use a stable `error.code`, human-readable `error.message`, optional fields, and the
  request ID response header.
- Admin mutations create an audit record in the same transaction as the mutation.

## Required realtime conventions

Every realtime event uses:

```json
{
  "eventId": "unique-event-id",
  "type": "quiz.question.activated",
  "sessionId": "session-id",
  "sequence": 42,
  "serverTime": "2026-10-20T00:00:00Z",
  "payload": {}
}
```

The server owns quiz status, question selection, timers, buzzer winners, answer windows, and
scores. Clients render snapshots and send intents; they never submit authoritative scores,
winners, deadlines, or team identities.
## Cutover result

The durable FastAPI contract has been implemented, integrated through the frontend, covered by
permission and persistence tests, and exercised through the runtime smoke flow. The former legacy
routes and Socket.IO transport have now been removed from the application runtime.
