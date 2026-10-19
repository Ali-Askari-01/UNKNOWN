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
| Auth | `POST /auth/admin/login`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/team/join` |
| Events | `GET/POST /events`, `GET/PATCH /events/{id}`, classes, rounds, schedule, announcements |
| Teams | `GET/POST /teams`, `GET/PATCH/DELETE /teams/{id}`, students, memberships, media |
| Questions | `GET/POST /questions`, `GET/PATCH/DELETE /questions/{id}`, import/validate |
| Quiz | `POST /quiz-blueprints`, `POST /quiz-sessions`, lifecycle actions, current state |
| Live | `POST /quiz-sessions/{id}/buzzer`, answer submission, judge, score adjustment |
| Results | class/event leaderboard, team history, round results, export |
| Audit | filtered audit search for authorized staff |

## Key request rules

- `POST` creates use idempotency keys where retries can duplicate records.
- `PATCH` requires a version/ETag for admin-edited resources.
- Pagination uses `limit`, `cursor`, and stable sort fields.
- Public team endpoints return only approved, public fields and media.
- Question-bank endpoints return answer keys only to authorized staff.
- Quiz start returns the session ID, public code, selected question count, and distribution summary—not answer keys.
- Score adjustment requires a reason and writes an audit record.

## Compatibility phase

During migration, add a compatibility adapter that maps the existing frontend calls (`/api/classes`, `/api/teams`, `/api/questions`, `/api/quizzes`, `/api/join`, `/api/answer`, `/api/leaderboard`) to FastAPI handlers. After the frontend switches to `/api/v1`, deprecate the legacy paths with telemetry and a removal date.
