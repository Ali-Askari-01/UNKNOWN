# UNKNOWN Delivery Roadmap, Risks, and Missing Decisions

## Current baseline

The repository currently contains a functioning Next.js/Node/Socket.IO prototype with service/repository boundaries, validation, authentication, quiz APIs, realtime buzzer flow, and an SQL Server schema design. Runtime data is still in-memory and the backend is still TypeScript.

## Recommended release sequence

1. Product and policy freeze.
2. SQL Server provisioning, migrations, seed data, and repository integration.
3. FastAPI foundation and contract tests.
4. Read-only FastAPI endpoints behind the existing frontend.
5. Team/question/quiz mutations with feature flags.
6. Realtime parity and buzzer race testing.
7. Cutover, soak test, backup/restore rehearsal, and event runbook.
8. Public showcase, media workflow, reporting, and next-edition tooling.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Ambiguous scoring rules | Incorrect winners | Approve a versioned scoring policy before migration |
| Student privacy/consent not defined | Compliance and trust risk | Define public/private fields, consent, retention, and deletion workflow |
| Media files stored in the database | Cost and backup growth | Object storage plus metadata table |
| Multiple backend workers with local websocket state | Split-brain buzzer behavior | Start single worker; add shared broker before scaling |
| SQL migration applied manually | Environment drift | Use Alembic/CI migration checks and a migration ledger |
| Frontend depends on legacy event shapes | Cutover breakage | Contract tests and compatibility adapter |
| Admin secrets in `.env.local` | Credential exposure | Secret manager, rotation, startup validation |
| Unbounded question selection | Repeated or unfair quiz | Blueprint distribution validation and deterministic session snapshot |
| Manual score edits | Disputed results | Append-only score entries and audit log |
| No restore rehearsal | False confidence in backups | Quarterly restore test and event-day recovery checklist |

## Decisions still needed

- SQL Server local/hosted target and authentication mode.
- Object storage provider and maximum file sizes/types.
- Whether the public site exposes student names/photos by consent.
- Exact question bank import format (CSV, JSON, admin UI, or all three).
- Tie-breaking, negative marking, bonus points, and score publication policy.
- Whether one quiz session is per class, per room, or per round.
- Whether team tokens are device-bound and how reconnection works.
- Event-day operator roles and who can override scores.
- Retention/deletion policy for student and media data.
