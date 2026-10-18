# Real-time Events

> Status: Phase 2 catalog. "Existing" events work today in `server.ts`;
> "planned" events land in Phases 6–7.

Transport: Socket.IO (websocket + polling fallback), same port as the app.
Rooms: `room:{classId}` (ix|x|xi), `admin` (admin panel sockets).

All payloads are validated with Zod on receipt. Clients may only emit intents —
never authoritative values (no scores, no winner names, no deadlines).

---

## Snapshot (`room:state`)

Emitted after every mutation to `room:{classId}` and to the requesting socket.

```ts
RoomSnapshot = {
  classId: "ix" | "x" | "xi",
  code: string | null,
  status: "waiting" | "open" | "active" | "paused" | "ended",
  questionNumber: number,          // 1-based; 0 before first question
  questionText: string | null,     // planned (Phase 6)
  buzzerState: "off" | "open" | "locked" | "expired",
  buzzerWinner: string | null,     // team name
  answerDeadline: number | null,   // epoch ms; clients render countdown only
  scores: Array<{ groupName, score, buzzCount }>,
  connectedCount: number
}
```

---

## Student → Server (existing)

| Event | Payload | Ack |
|---|---|---|
| `room:join` | `{ classId, code, groupName }` | `{ ok, snapshot }` or `{ ok:false, error }` |
| `buzzer:press` | `{}` | `{ ok, snapshot }` or `{ ok:false, error }` |
| `room:getState` | `{}` | `{ ok, snapshot }` |

## Student → Server (planned)

| Event | Payload | Notes |
|---|---|---|
| `answer:submit` | `{ answer: string }` | Phase 7; only the buzzer winner's socket may emit. REST `POST /api/answer` remains the primary path. |

## Admin → Server (existing)

Each requires `socket.data.isAdmin`; otherwise the ack is `{ ok:false, error:"forbidden" }`.

| Event | Payload |
|---|---|
| `admin:join` | `{}` — joins room `admin`, acks with all snapshots |
| `admin:openRoom` | `{ classId }` |
| `admin:resetRoom` | `{ classId }` |
| `admin:setCode` | `{ classId, code }` |
| `admin:startQuiz` | `{ classId }` |
| `admin:endQuiz` | `{ classId }` |
| `admin:activateBuzzer` | `{ classId }` |
| `admin:disableBuzzer` | `{ classId }` |
| `admin:reEnableBuzzer` | `{ classId }` |
| `admin:markCorrect` | `{ classId, points }` |
| `admin:markIncorrect` | `{ classId, deduct }` |
| `admin:adjustScore` | `{ classId, groupName, delta }` |
| `admin:nextQuestion` | `{ classId }` |
| `admin:resetQuestion` | `{ classId }` |
| `admin:getStates` | `{}` |

## Admin → Server (planned)

| Event | Payload | Notes |
|---|---|---|
| `admin:pauseQuiz` | `{ classId }` | Phase 6 — cancels timers, closes buzzer |
| `admin:resumeQuiz` | `{ classId }` | Phase 6 |
| `admin:reopenBuzzer` | `{ classId }` | Phase 6 — reopen after expiry/incorrect; excludes already-buzzed teams |
| `admin:prepareQuiz` | `{ classId }` | Phase 6 — bind question bank, initialize room |

## Server → Clients (existing)

| Event | Audience | Payload |
|---|---|---|
| `room:state` | `room:{classId}` + acking socket | `RoomSnapshot` |
| `buzzer:expired` | `room:{classId}` | `{ classId, questionNumber }` — fired by the 20s server timer |

## Server → Clients (planned)

| Event | Audience | Payload |
|---|---|---|
| `buzzer:winner` | `room:{classId}` | `{ classId, teamName, answerDeadline }` |
| `buzzer:reopened` | `room:{classId}` | `{ classId, questionNumber }` |
| `question:started` | `room:{classId}` | `{ classId, questionNumber }` |
| `quiz:status` | `room:{classId}` + `admin` | `{ classId, status }` |
| `answer:result` | `room:{classId}` | `{ classId, teamName, correct, pointsAwarded }` |
| `leaderboard:update` | `room:{classId}` + `admin` | `{ classId, entries }` |

---

## Atomic First-Winner Selection

Node.js handles socket events serially on a single thread. For `buzzer:press`:

1. Reject if `buzzerState !== "open"`.
2. Reject if `buzzedThisQuestion.has(team)`.
3. Commit: set winner, `buzzerState = "locked"`, add team to `buzzedThisQuestion`,
   start the 20s timer — all synchronously before yielding.
4. Any later press in the same tick or afterward fails step 1 or 2.

No locks or queues are required; correctness comes from never awaiting between the
check and the commit.

## Timing Authority

- Server: `setTimeout` per room for the answer window; cleared on pause/finish/reset.
- Client: countdown UI computed from `answerDeadline - Date.now()`, display only.
- On expiry the server emits `buzzer:expired` and updates the snapshot; clients never
  transition state on their own clock alone.
