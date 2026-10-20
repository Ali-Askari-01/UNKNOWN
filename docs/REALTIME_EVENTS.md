# FastAPI Realtime Events

The production quiz transport is the native FastAPI WebSocket endpoint:

```text
WebSocket /api/v1/ws/quiz/{session_id}
```

The browser sends `Sec-WebSocket-Protocol: auth.{signed-admin-or-team-token}`. The token is
validated before the connection is accepted and is never placed in the URL. Team tokens are
scoped to the target session. The browser receives sanitized state; answer keys and authoritative
score fields are never exposed to students.

## Server event envelope

Lifecycle broadcasts use the following shape:

```json
{
  "type": "quiz.state.changed",
  "sessionId": "session-id",
  "sequence": 42,
  "serverTime": "2026-10-20T00:00:00Z",
  "payload": {}
}
```

## Events

| Event | Audience | Purpose |
|---|---|---|
| `quiz.state.snapshot` | Admin/team | Initial sanitized session state and currently open question |
| `quiz.state.changed` | Admin/team | Persisted lifecycle or question transition |
| `quiz.buzzer.accepted` | Admin/team | Database-confirmed winning buzzer and answer deadline |
| `quiz.answer.submitted` | Admin/team | Pending answer entered for staff judging |
| `quiz.answer.judged` | Admin/team | Staff decision and resulting score delta |
| `quiz.snapshot.request.ack` | Requesting client | Acknowledges a snapshot refresh request |
| `quiz.ping.ack` | Requesting client | Connection health acknowledgement |

## Client messages

Clients send intents only; the server remains authoritative for status, questions, winners,
deadlines, answer eligibility, and scores.

| Message | Purpose |
|---|---|
| `quiz.snapshot.request` | Request a fresh state acknowledgement |
| `quiz.ping` | Keepalive/health check |

Mutations use versioned REST endpoints:

- `POST /api/v1/quiz-sessions/{session_id}/questions/{question_id}/buzzer`
- `POST /api/v1/quiz-sessions/{session_id}/answers`
- `POST /api/v1/admin/quiz-sessions/{session_id}/actions/{action}`
- `POST /api/v1/admin/quiz-sessions/{session_id}/answers/{answer_id}/judge`

The buzzer winner is selected by a database transaction and filtered unique constraint. Clients
render server timestamps and deadlines; they never decide winners or scores locally.

Snapshot and broadcast sequence numbers are allocated by the SQL-backed realtime event ledger. A
database lock row is held until each ledger transaction commits, so concurrent workers cannot
commit a higher identity before a lower identity and cause a relay cursor to skip an event. Each
worker polls committed broadcast events and delivers them to its local WebSocket connections.
Snapshots include every joined team,
including zero-score teams, and reflect persisted score publication. The browser client reconnects
with bounded exponential backoff up to 10 seconds; an intentional room leave cancels pending
reconnects.
