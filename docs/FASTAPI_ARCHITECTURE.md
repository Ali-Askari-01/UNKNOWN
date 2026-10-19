# FastAPI Target Architecture

## Repository layout

```text
backend/
  app/
    main.py
    api/v1/                 # routers only: parse, authorize, call service
    core/                   # settings, logging, security, request IDs
    db/                     # engine, sessions, models, migrations config
    domain/                 # enums, value objects, business errors
    schemas/                # Pydantic request/response contracts
    repositories/           # interfaces and SQLAlchemy implementations
    services/               # transaction-owning use cases
    realtime/               # websocket manager and event handlers
    policies/               # role, class, team, publication permissions
    workers/                # cleanup, exports, media processing jobs
  tests/
    unit/
    integration/
    contract/
    realtime/
  pyproject.toml
```

## Request flow

```text
Router -> dependency (settings/session/db) -> policy -> service -> repository -> SQL Server
                                                        └-> audit/outbox -> realtime broadcast
```

Routers must not contain scoring logic, SQL queries, or direct ORM mutation. Services coordinate a use case and transaction. Repositories translate between domain models and persistence models. Schemas prevent accidental answer-key or private-field leakage.

## SQLAlchemy strategy

- Use typed SQLAlchemy 2.x models and explicit relationships.
- Prefer repository query methods over exposing `Session` to business code.
- Use `AsyncSession` for API request paths and a bounded pool.
- Keep Alembic migration models separate from public Pydantic schemas.
- Use UTC-aware application timestamps while storing SQL Server `datetime2(3)` consistently.
- Add query timeouts and pagination to admin/report endpoints.

## FastAPI application lifecycle

Startup validates settings, initializes logging/tracing, checks database readiness, and loads only safe caches. Shutdown closes the engine and realtime manager. Health endpoints distinguish process liveness from dependency readiness.

## Migration boundary

Phase 1 keeps the current TypeScript service behavior as the reference. Phase 2 implements Python repositories and services against the same concepts. Phase 3 routes the frontend to FastAPI. Phase 4 removes the Node custom server only after parity evidence.
