# Project Description

## Overview

UNKNOWN is a live quiz competition website for a school event spanning three class tracks: **Class IX, Class X, and Class XI**. It runs buzzer-style rounds where student teams compete in real time, with an admin controlling the flow of the event.

## Panels

### Admin Panel
- Single admin account (env-configured, no database).
- Manages all three class tracks independently.
- Controls: quiz codes, class/team management, questions, quiz lifecycle (start/pause/resume/finish), buzzer activation, answer validation (correct/incorrect), score adjustments, and the live leaderboard.

### Student Panel
- Students visit `/quiz`, pick their class, enter the quiz code shown by the admin, and select their team/group.
- During a round they press a buzzer when it opens; the first valid press wins the right to answer.
- The answering team then has a **20-second window** to submit an answer.

## Competition Rules (implemented/planned)

- One buzzer round per question; the buzzer opens only when the admin activates it.
- First valid buzzer press wins (atomic server-side selection — simultaneous presses are resolved on the server, never in the browser).
- Winner team gets an answering window of 20 seconds (server-authoritative timer).
- On timeout, the admin can mark the answer incorrect or re-open the buzzer for other teams.
- Correct answers award points; incorrect answers may deduct points (admin-configurable).
- Scores feed a live leaderboard that updates for all connected clients.

## Technology

- Next.js 16 (App Router) + React 19 + TypeScript (strict)
- Custom Node server (`server.ts`) hosting Next.js and Socket.IO on one port
- Tailwind CSS 4, shadcn-style UI
- pnpm package manager

## Storage — Important Limitation (this phase)

**There is no database.** All state (teams, questions, quizzes, scores, buzzer state) lives in
in-memory repositories inside the Node process.

> **Temporary state resets on every server restart.** Quiz sessions, scores, and joined
> teams do **not** survive restarts and are **not** production persistence. This phase
> intentionally ships with a clean repository interface so a real database can be added
> later without rewriting business logic.

See `docs/ARCHITECTURE.md` for the repository pattern and `docs/SECURITY.md` for
operational caveats.
