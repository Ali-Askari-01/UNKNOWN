# FastAPI API Contract

## Conventions

- Base path: `/api/v1`.
- JSON uses camelCase at the public boundary if that matches the existing frontend; Python models may use snake_case internally.
- Every response includes a request/correlation ID header.
- Errors use:

```json
{
  "error": {
    "code": "QUIZ_NOT_ACTIVE",
    "message": "The quiz is not accepting buzzer presses.",
    "fields": []
  },
  "requestId": "..."
}
```

## Resource groups

| Group | Endpoints |
|---|---|
| Auth | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/team/join` |
| Events | `GET/POST /events`, `GET/PATCH /events/{id}`, classes, rounds, schedule, announcements |
| Teams | `GET/POST /teams`, `GET/PATCH/DELETE /teams/{id}`, students, memberships, media |
| Questions | `GET/POST /questions`, `GET/PATCH/DELETE /questions/{id}`, import/validate |
| Quiz | `POST /quiz-blueprints`, `POST /quiz-sessions`, lifecycle actions, current state |
| Live | `POST /quiz-sessions/{id}/buzzer`, answer submission, judge, score adjustment |
| Results | class/event leaderboard, team history, round results, export |
| Audit | filtered audit search for authorized staff |

## Key request rules

- `POST /auth/login` issues an eight-hour `HttpOnly`, `SameSite=Lax` cookie named
  `unknown_admin_session`; bearer authentication remains supported for service clients and tests.
- `POST /auth/logout` clears the backend session cookie.
- `POST /auth/team/join` validates the quiz code and team/class relationship, creates or reuses the
  participant, and issues an eight-hour scoped `unknown_team_session` cookie.
- Participant and answer mutations require the scoped team session; clients cannot choose an
  unrelated participant ID.

- Retry-sensitive mutation endpoints accept idempotency keys; team join, answer submission, answer
  judging, and admin session actions persist and replay successful responses. Other create endpoints
  rely on database uniqueness and return a conflict when a duplicate resource is submitted.
- `PATCH` requires a version/ETag for admin-edited resources.
- Pagination uses `limit`, `cursor`, and stable sort fields.
- Public team endpoints return only approved, public fields and media.
- Question-bank endpoints return answer keys only to authorized staff.
- Quiz start returns the session ID, public code, selected question count, and distribution summary—not answer keys.
- Score adjustment requires a reason and writes an audit record.
- Quiz lifecycle actions are exposed as `POST /admin/quiz-sessions/{id}/actions/{action}` for
  `open`, `start`, `pause`, `resume`, `advance`, and `end`; invalid transitions return `409`.
- `POST /quiz-sessions/{id}/questions/{questionId}/buzzer` requires the scoped team session and
  persists the first accepted winner; later presses return `409`.
- `POST /quiz-sessions/{id}/answers` requires the winning team token and creates a pending final
  submission; it does not score or expose answer-key validation to the participant.
- `GET /admin/quiz-sessions/{id}/answers` returns the staff-only judging queue, including the
  submitted answer and team name.
- `POST /admin/quiz-sessions/{id}/answers/{answerId}/judge` is idempotency-protected: it accepts
  one correctness decision, creates the score ledger entry, and broadcasts the judged result.

## Compatibility phase

The frontend now uses the versioned `/api/v1` routes directly. The former compatibility paths have
been removed so there is one browser-to-backend contract and one quiz authority.
