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
- FastAPI + SQLAlchemy/Alembic API with native authenticated WebSocket realtime
- SQL Server production persistence with SQLite isolated development fallback
- Tailwind CSS 4, shadcn-style UI
- pnpm package manager

## Storage and authority

FastAPI and SQL Server are the authority for teams, questions, quiz sessions, participants,
buzzer arbitration, answers, scores, and audit records. Next.js renders the UI and proxies
versioned `/api/v1` requests to FastAPI.

Quiz state survives API restarts through SQL Server. Production deployments require the documented
Alembic migration, backup/restore, secret-manager, load/soak, and monitoring gates before event
cutover.

See `docs/ARCHITECTURE.md`, `docs/INTEGRATION_AUDIT.md`, and `docs/SECURITY.md` for the current
runtime contract and operational caveats.
