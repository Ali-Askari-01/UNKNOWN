# Master Implementation Roadmap

## Workstream order

| Stage | Database | FastAPI | Frontend/operations |
|---|---|---|---|
| 1 | Decisions, SQL Server, migrations | Skeleton and health | Contract freeze |
| 2 | Seed/import and repositories | Read-only parity | Shadow comparison |
| 3 | Durable quiz/score transactions | CRUD/auth | Admin feature flag |
| 4 | Backup, indexes, audit | Quiz/realtime | Student feature flag |
| 5 | Load/restore tests | Cutover | Event rehearsal |
| 6 | Reporting and next edition | Retire Node | Public showcase |

## Weekly execution cadence

1. Select one vertical slice: team CRUD, question bank, quiz start, or scoring.
2. Write/approve contract and migration first.
3. Implement repository, service, API, and frontend adapter.
4. Add unit, integration, contract, and permission tests.
5. Run migration, smoke test, and rollback check in staging.
6. Record evidence and unresolved risks before moving to the next slice.

## Go/no-go gates

- Gate A: schema and policy approved.
- Gate B: FastAPI read parity approved.
- Gate C: durable writes and audit approved.
- Gate D: realtime correctness approved.
- Gate E: backup/restore and event rehearsal approved.

## What was missing and is now covered

- Product requirements and success criteria.
- Technical target architecture and service boundaries.
- Database rules, dictionary, migrations, security, backup, and testing.
- FastAPI architecture, API contracts, realtime/auth, security, testing, and deployment.
- Phase-by-phase database and backend migration plans.
- Open decisions, risks, and operational gaps.
