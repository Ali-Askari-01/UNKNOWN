# API Documentation

> Status: Phase 2 contracts. Endpoints marked **planned** are not implemented yet.
> All request bodies are validated with Zod server-side (Phase 3+). Browser validation
> is never trusted.

Base URL: same origin as the app. All admin endpoints require the
`quiz_admin_session` HttpOnly cookie (see `docs/SECURITY.md`).

Conventions:
- Success: JSON body, HTTP 200/201.
- Errors: JSON `{ "error": string }` with 400 (validation), 401 (unauthenticated),
  403 (forbidden), 404 (not found), 409 (conflict), 503 (misconfiguration).
- `classId` is always one of `"ix" | "x" | "xi"`.

---

## Authentication (existing)

### POST /api/admin/login
Login with username/password. Sets session cookie on success.
- Body: `{ "username": string, "password": string }`
- 200: `{ "ok": true }`
- 401: invalid credentials; 503: `ADMIN_PASSWORD_HASH` not configured

### POST /api/admin/logout
Clears the session cookie. 200: `{ "ok": true }`

### GET /api/admin/me
Verifies the session. 200: `{ "authenticated": true }` | 401

---

## Classes (planned — Phase 5)

### GET /api/classes
List class tracks with team counts.
- 200: `{ classes: Array<{ id, roman, label, level, teamCount }> }`

### GET /api/classes/:classId
Single class detail. 404 if unknown classId.

---

## Teams (planned — Phase 5)

### GET /api/teams?classId=ix
List teams for a class. 200: `{ teams: Team[] }`
```ts
Team = { id, classId, name, members: string[], score, buzzCount }
```

### POST /api/teams
Create a team. Admin only.
- Body: `{ classId, name: string (2..40), members: string[] (1..10) }`
- 201: `{ team: Team }`; 409: duplicate name in class.

### PATCH /api/teams/:teamId
Update name/members. Admin only. 200: `{ team: Team }`

### DELETE /api/teams/:teamId
Remove a team. Admin only. 200: `{ ok: true }`

---

## Questions (planned — Phase 5)

### GET /api/questions?classId=ix
List question bank for a class. Admin only.
- 200: `{ questions: Question[] }`
```ts
Question = {
  id, classId, order, text,
  options: string[] | null,     // null for open-ended buzzer questions
  correctAnswer: string,
  points: number                // default 10
}
```

### POST /api/questions
Create a question. Admin only.
- Body: `{ classId, text (5..500), options?, correctAnswer (1..200), points? (1..100) }`
- 201: `{ question: Question }`

### PATCH /api/questions/:questionId
Update a question. Admin only.

### DELETE /api/questions/:questionId
Delete a question. Admin only. Reorders remaining questions for that class.

---

## Quizzes & Codes (planned — Phase 5)

### POST /api/quizzes
Prepare a quiz for a class (initializes a room from the question bank).
- Body: `{ classId }`
- 201: `{ quiz: Quiz }`
```ts
Quiz = {
  id, classId, code, status: "waiting"|"open"|"active"|"paused"|"ended",
  currentQuestionIndex, questionCount
}
```

### POST /api/quizzes/:quizId/start | /pause | /resume | /finish
Lifecycle transitions. Admin only. 200: `{ quiz: Quiz }` |
409 if the transition is invalid for the current status.

### POST /api/quizzes/:quizId/code
Rotate the join code. Admin only. 200: `{ code: string }` (new code).

### GET /api/quizzes/:classId
Current quiz state for a class. 200: `{ quiz: Quiz | null, snapshot: RoomSnapshot }`

---

## Student Join (planned — Phase 5)

### POST /api/join
Join a class room as a team. Public endpoint (rate-limited).
- Body: `{ classId, code: string, groupName: string }`
- 200: `{ token: string, team: { name, members }, snapshot: RoomSnapshot }`
- 401: wrong code; 404: unknown class/group; 409: room not joinable (ended).

The returned token authenticates the team's socket and answer submissions.

---

## Answers & Leaderboard (planned — Phase 7)

### POST /api/answer
Submit an answer for the team that won the buzzer.
- Auth: team token.
- Body: `{ answer: string (1..500) }`
- 200: `{ correct: boolean, pointsAwarded: number, snapshot }`
- 409: not your team's turn / window expired / no open question.

### GET /api/leaderboard?classId=ix
Live standings. Public.
- 200: `{ entries: Array<{ rank, teamName, score, buzzCount }> }`

---

## Admin API rules

- Every admin endpoint (except login) must:
  1. Verify the session signature (constant-time).
  2. Validate the body/params with the matching Zod schema.
  3. Call a service — route handlers contain no business logic.
- Student-facing endpoints never accept a score, role, or winner field from the client.
