# Quiz Flow

> Status: Phase 2 design. Implemented across Phases 6–7; the legacy
> `lib/quiz-state.ts` implementation was removed in Phase 8.

## Actors

- **Admin** — runs the event from `/admin/durable-quiz`.
- **Teams** — student groups on `/quiz` (one shared screen per team).
- **Server** — sole authority for state, timers, and winner selection.

## Current Standard Quiz Rules

The admin can create a standard blueprint for a selected class. It contains exactly 30
questions: 10 `CONCEPTUAL`, 5 `RIDDLE`, 5 `THEORY`, and 10 `DEBUGGING`. Session creation
randomly selects distinct eligible questions from the database-backed question bank and
fails with `INSUFFICIENT_QUESTION_BANK` if any category is short.

Only `RIDDLE` questions use the buzzer. Conceptual, theory, and debugging answers can be
submitted directly by the team's session identity. MCQs are checked against their saved
correct option; other question types are checked against one or more admin-maintained
accepted answers. The answer key is snapshotted into each quiz session and is never exposed
to student clients. Teams have one final submission per question; scores are recorded for
the team, regardless of which member is operating the shared team session.

| Submission | Score |
|---|---:|
| Correct non-riddle | `+P` |
| Incorrect non-riddle | `0` |
| Correct riddle | `+2P` |
| Incorrect riddle | `−P` |

Here `P` is the question's configured point value. Incorrect riddle answers release the
buzzer for another team; a correct riddle answer closes that question. A legacy question
without a usable answer key is sent to manual review where applicable, rather than being
silently marked wrong.

## Lifecycle

```
WAITING ──open code──► OPEN ──start──► ACTIVE ⇄ PAUSED ──finish──► ENDED
                                          │
                                          └── (per question loop) ──┘
```

| Status | Meaning |
|---|---|
| `waiting` | Room created; no code issued; students cannot join. |
| `open` | Join code active; teams may join between questions. |
| `active` | Quiz running; questions served; buzzer available only for riddles. |
| `paused` | Admin paused; buzzer forced closed; timer cancelled; no scoring. |
| `ended` | Final; no further joins, buzzes, or answers. |

## Per-Question Sequence

1. **Question presented** — the server loads the saved question snapshot, answer key, and
   question type; clients receive only the prompt and public options.
2. **Non-riddles** — any joined team may submit during the question window. MCQs are graded
   against the correct option; other types are graded against admin-maintained accepted answers.
3. **Riddles** — the server opens the buzzer. The first team to buzz gets the answer window.
   A correct answer scores and closes the question. A wrong answer deducts points and releases
   the buzzer to another team; an expired winner can also be replaced.
4. **Scoring** — the server writes the final answer and score entry atomically. Manual review
   remains available for legacy questions that lack a usable saved answer key.
5. **Next question** — the admin advances, and the server opens the next persisted question.

## Timing Rules

- The configured answer window is enforced by the API using persisted timestamps; clients
  render the countdown from the server deadline.
- Non-riddle windows start when a question opens. Riddle answer windows start when a team wins
  the buzzer.
- After a wrong riddle answer, that team cannot submit again for the same question.

## Joining Rules

- Students join only while status is `open` (or between questions while `active`,
  configurable) with the current code.
- A group name must match a known team for that class.
- One active socket identity per team per room; a reconnect replaces the previous one.

## Scoring Rules

- Correct non-riddle: `+P`; incorrect non-riddle: `0`.
- Correct riddle: `+2P`; incorrect riddle: `-P`.
- Manual adjustment: admin may add/remove arbitrary deltas (audited in logs).
- Leaderboard order: total score desc, then buzzCount asc as tiebreaker.

## End of Quiz

`POST /api/v1/admin/quiz-sessions/{session_id}/actions/end` forces the buzzer closed, persists the
`ENDED` state, and broadcasts the final durable state. Scores and audit records survive restart.
