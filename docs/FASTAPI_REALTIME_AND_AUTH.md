# FastAPI Realtime and Authentication Design

## Authentication

- Staff: secure HttpOnly session cookie or short-lived access token plus refresh/revocation strategy.
- Team: join code is exchanged once for a short-lived, team-scoped signed token; the token identifies the team, not a student account.
- Realtime handshake validates the token server-side before joining a session room.
- Every mutation checks role, event/session scope, team ownership, and current quiz state.
- Logout/revocation invalidates staff sessions; rotating event codes invalidates team access as appropriate.

## Websocket event envelope

```json
{
  "eventId": "uuid",
  "type": "quiz.state.updated",
  "sessionId": "uuid",
  "sequence": 42,
  "serverTime": "2026-10-19T12:00:00Z",
  "payload": {}
}
```

Required event families: session state, question opened, buzzer opened, buzzer accepted, buzzer rejected, answer window started, answer judged, score updated, session paused/resumed/ended, and error.

## Buzzer correctness

1. Validate token and participant membership.
2. Validate session/question state.
3. Insert press with server timestamp.
4. Atomically claim the winner using a transaction and unique filtered winner index.
5. Create answer window and broadcast the authoritative state.
6. Reject later presses without leaking the answer key.

The in-process Python lock is only a local optimization. If more than one FastAPI worker is used,
winner selection must rely on SQL Server transaction/constraint behavior and the SQL-backed
realtime event relay; never rely on process-local memory for correctness.

## Reconnect behavior

- Client reconnects with the team token.
- Server revalidates session membership and returns the latest sanitized snapshot.
- Client uses sequence numbers to detect missed events and requests a snapshot.
- Duplicate answer/score requests are rejected or safely replayed using idempotency keys.
