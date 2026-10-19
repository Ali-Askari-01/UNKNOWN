# Database Security, Backup, and Operations

## Access model

- FastAPI runtime uses a dedicated login with only required CRUD/execute permissions on `competition`.
- Migration runner uses a separate elevated login and is never embedded in the application container.
- Analysts receive read-only views, not base-table write access.
- Staff actions remain authorized in FastAPI even if a database user has broad access.
- Production connections require encrypted transport and certificate validation.

## Sensitive data

- Passwords are Argon2id/bcrypt hashes only.
- Student reference fields and photos are private by default until consent/publication is recorded.
- Answer keys are server-side only and excluded from public schemas, logs, traces, and error messages.
- Object-storage keys are private implementation details; public URLs should be short-lived signed URLs.
- Secrets come from a secret manager or protected deployment environment, never Git.

## Backup and recovery

- Define recovery point objective and recovery time objective before production. Recommended initial target: RPO 15 minutes, RTO 60 minutes.
- Use full, differential, and transaction-log backups appropriate to the chosen SQL Server edition.
- Encrypt backups and restrict restore permissions.
- Perform a restore rehearsal before every major event and at least quarterly.
- Verify row counts, latest migration, published scores, and audit continuity after restore.

## Monitoring

- Database connectivity/readiness.
- Connection pool exhaustion and query latency.
- Deadlocks, failed transactions, lock waits, and migration failures.
- Quiz session starts, active connections, buzzer rejection rate, answer latency, and score publication errors.
- Backup age and restore-test result.

## Operational controls

- Freeze schema migrations during a live quiz unless emergency procedure is approved.
- Do not restart all API workers during an active buzzer round.
- Retain an event-day operator checklist with contacts, backup verification, room codes, and recovery commands.
- Use temporal tables or equivalent history for high-value mutable operational tables where point-in-time reconstruction is required.
