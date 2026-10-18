# Quiz Flow

> Status: Phase 2 design. Buzzer mechanics partially exist in `lib/quiz-state.ts`;
> question-driven flow, pause/resume, and reopen rules land in Phases 6–7.

## Actors

- **Admin** — runs the event from `/admin/quiz`.
- **Teams** — student groups on `/quiz` (one shared screen per team).
- **Server** — sole authority for state, timers, and winner selection.

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
| `active` | Quiz running; questions served; buzzer operational. |
| `paused` | Admin paused; buzzer forced closed; timer cancelled; no scoring. |
| `ended` | Final; no further joins, buzzes, or answers. |

## Per-Question Sequence

1. **Question presented** — server advances `currentQuestionIndex` (admin:
   `admin:nextQuestion` or automatic after scoring). All clients receive
   `room:state` with the new question number and `buzzerState: "off"`.
2. **Buzzer activation** — admin calls `admin:activateBuzzer`. Server sets
   `buzzerState: "open"`, records `buzzerActivatedAt`. Clients show the press button.
3. **Buzzer press** — a team emits `buzzer:press`. Server:
   - rejects if buzzer not open, presser already buzzed this question, or a winner
     already exists;
   - otherwise atomically locks the buzzer (`locked`), records the winner team,
     starts the **20-second answer window** (`answerDeadline = now + 20s`).
   - Broadcasts `buzzer:winner` + `room:state`.
4. **Answer window** — only the winning team may submit (REST `POST /api/answer` or
   admin-entered on their behalf). Server counts down authoritatively.
5. **Resolution** (one of):
   - **Correct** — `ScoringService.award(points)`; question closed.
   - **Incorrect** — deduct (admin-configurable) and either:
     - **re-open the buzzer** for the remaining teams (teams that already buzzed are
       excluded via `buzzedThisQuestion`), or
     - **skip** the question.
   - **Timeout** — at T+20s the server auto-sets `buzzerState: "expired"`, cancels the
     window, broadcasts `buzzer:expired`. Admin then marks incorrect / reopens / skips.
6. **Next question** — admin advances; `buzzedThisQuestion` clears; loop repeats from 1.

## Timing Rules

- The 20-second window is enforced by a server `setTimeout`; clients only render a
  countdown from `answerDeadline`.
- Pausing the quiz cancels any open window; resuming does not restore it — the admin
  re-opens the buzzer.
- Re-opening the buzzer after expiry/incorrect keeps the same question and the same
  exclusion set (already-buzzed teams stay locked out).

## Joining Rules

- Students join only while status is `open` (or between questions while `active`,
  configurable) with the current code.
- A group name must match a known team for that class.
- One active socket identity per team per room; a reconnect replaces the previous one.

## Scoring Rules

- Correct: `+points` (question's point value).
- Incorrect: `-deduct` (admin-entered amount; may be 0).
- Manual adjustment: admin may add/remove arbitrary deltas (audited in logs).
- Leaderboard order: total score desc, then buzzCount asc as tiebreaker.

## End of Quiz

`admin:endQuiz` forces buzzer closed, cancels timers, sets `ended`, and emits a final
`leaderboard:update`. State remains in memory until restart or admin reset.
