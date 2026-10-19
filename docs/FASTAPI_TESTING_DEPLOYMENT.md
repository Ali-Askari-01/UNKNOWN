# FastAPI Testing and Deployment

## Test layers

1. Unit: domain rules, distributions, scoring, authorization policies.
2. Repository integration: SQL Server migrations, CRUD, constraints, transactions.
3. API contract: request validation, error envelopes, pagination, redaction, legacy compatibility.
4. Realtime: reconnect, sequence gaps, simultaneous buzzer, timeout, pause/resume.
5. Security: role matrix, token expiry/replay, rate limiting, CORS/CSRF, upload validation.
6. End-to-end: frontend against a staged FastAPI + SQL Server stack.

## Deployment topology

```text
HTTPS ingress / reverse proxy
        │
FastAPI container(s) ─── SQL Server
        │
        ├── shared realtime broker when horizontally scaled
        └── object storage for media
```

Start with one FastAPI worker for the live event unless shared websocket coordination is implemented. Scale only after proving event ordering, SQL transactions, and broadcast delivery across workers.

## CI gates

- Format/lint/type-check.
- Unit and integration tests.
- Fresh-database migration test.
- Contract diff check.
- Dependency and secret scan.
- Container build and smoke test.
- Staging migration dry run.

## Release checklist

- Migration backup and restore point verified.
- Required secrets present and validated.
- Database readiness and health endpoints green.
- Frontend points to the intended API origin.
- Admin login and team join smoke-tested.
- Quiz start, buzzer, answer, scoring, and leaderboard tested.
- Logs/metrics/traces visible.
- Rollback version and event-day contact list confirmed.
