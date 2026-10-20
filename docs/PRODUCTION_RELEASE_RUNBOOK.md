# Production Release and Restore Runbook

This is the operator checklist for the FastAPI/SQL Server deployment. It is intentionally
separate from the application container: migration credentials and backup credentials must not be
available to the runtime process.

## 1. Preflight

Set the following in the deployment secret manager, not in Git:

```text
BACKEND_ENVIRONMENT=production
BACKEND_WORKERS=1
BACKEND_DATABASE_URL=mssql+aioodbc://...
BACKEND_DB_POOL_SIZE=10
BACKEND_DB_MAX_OVERFLOW=20
BACKEND_DB_POOL_TIMEOUT=30
BACKEND_DB_POOL_RECYCLE=1800
BACKEND_AUTH_SECRET=<random-32-byte-secret>
BACKEND_ADMIN_USERNAME=<operator-name>
BACKEND_ADMIN_PASSWORD_HASH=<bcrypt-hash>
# BACKEND_ADMIN_PASSWORD is intentionally not required in production.
BACKEND_ALLOW_DEV_ADMIN=false
BACKEND_RUN_MIGRATIONS=false
BACKEND_CORS_ORIGINS=https://<frontend-origin>
BACKEND_TRUSTED_HOSTS=<api-host>,<frontend-host>
NEXT_PUBLIC_FASTAPI_WS_URL=wss://<api-host>
```

To rotate the administrator password, run the checked-in generator locally or in the approved
operator environment. It prompts twice, never accepts the password as a command-line argument, and
prints only the bcrypt hash:

```powershell
Push-Location backend
python scripts/generate_password_hash.py --rounds 12
Pop-Location
```

Update `BACKEND_ADMIN_PASSWORD_HASH` in the deployment secret manager, restart the API workers,
and rerun production preflight plus the admin-login smoke. Rotating the bcrypt hash changes future
logins; rotate `BACKEND_AUTH_SECRET` in the same approved operation when all existing signed admin
and team tokens must be invalidated immediately.

Confirm the release gates before opening the maintenance window:

```powershell
corepack pnpm check
```

After the backup and migration steps below, run the preflight. It prints only pass/fail summaries
and fails when production-only settings are missing, the database cannot be reached, a FastAPI-owned
table or column is missing, or the installed Alembic revision is not the expected release head.
Unrelated legacy tables are deliberately outside this contract and are not auto-dropped. After the
API is running, repeat it with `--base-url https://<api-host>` to include the readiness endpoint
check.

## 2. Backup before migration

Use a SQL Server operator identity with backup permission. Replace the database, server, and
output path with environment-specific values; never interpolate application secrets into this
command.

```powershell
sqlcmd -S <server> -d master -E -Q "BACKUP DATABASE [<database>] TO DISK = N'<backup-file>.bak' WITH COPY_ONLY, INIT, COMPRESSION, CHECKSUM, STATS = 10"
sqlcmd -S <server> -d master -E -Q "RESTORE VERIFYONLY FROM DISK = N'<backup-file>.bak' WITH CHECKSUM"
```

SQL Server Express does not support backup compression; omit `COMPRESSION` for Express rehearsal
or deployments.

Record the backup timestamp, file checksum, database name, current Alembic revision, and operator
in the release log.

## 3. Migration and smoke test

Run the migration from the separate migration runner identity, never from a rolling web worker.
The web container leaves migrations disabled unless explicitly overridden for a controlled local
operation. Then run the release preflight:

```powershell
Push-Location backend
python -m alembic current
python -m alembic upgrade head
python scripts/production_preflight.py --expected-head 0010_auto_quiz_rules
Pop-Location
```

Validate the application identity:

```powershell
Invoke-WebRequest https://<api-host>/health/live
Invoke-WebRequest https://<api-host>/health/ready
```

The event smoke test must cover admin login, session creation, open/start, team join, buzzer,
answer submission, judging, leaderboard, and WebSocket snapshot delivery. The checked-in backend
tests include the same transaction rules plus simultaneous buzzer arbitration.

Run the disposable end-to-end smoke with the administrator password supplied through the environment
variable named by `--admin-password-env`; the script never prints credentials or tokens:

```powershell
$env:SMOKE_ADMIN_PASSWORD = '<disposable-admin-password>'
Push-Location backend
python scripts/e2e_smoke.py --base-url https://<api-host> --class-code IX
Pop-Location
```

For a disposable active one-question session, run the bounded multi-team race check:

```powershell
Push-Location backend
python scripts/quiz_load_smoke.py --base-url http://127.0.0.1:8000 --quiz-code <ACTIVE-CODE> --team-limit 5
Pop-Location
```

The command must report exactly one `201` buzzer result and `409` responses for every other team.

For a bounded pre-event soak against disposable or approved staging data:

```powershell
$env:SMOKE_ADMIN_PASSWORD = '<disposable-admin-password>'
Push-Location backend
python scripts/quiz_soak_smoke.py --base-url https://<api-host> --class-code IX --iterations 10 --max-concurrency 3
Pop-Location
```

Retain the reported durations, completed-session count, reconnect invariant, and score-publication
invariant with the release evidence. Keep the iteration and concurrency limits within the approved
database capacity.

## 4. Restore rehearsal

Restore into a separate rehearsal database, never over the live database:

```powershell
sqlcmd -S <server> -d master -E -Q "RESTORE DATABASE [<database>_restore_rehearsal] FROM DISK = N'<backup-file>.bak' WITH MOVE '<logical-data-name>' TO '<rehearsal-data-file>.mdf', MOVE '<logical-log-name>' TO '<rehearsal-log-file>.ldf', RECOVERY, REPLACE, STATS = 10"
```

Point a temporary API process at the rehearsal database and verify:

1. `alembic current` equals the release revision.
2. Counts for editions, teams, quiz sessions, answer submissions, score entries, and audit rows
   match the recorded pre-backup counts.
3. The latest published score and its linked answer submission are present.
4. The latest audit row is present and chronological ordering is intact.
5. `/health/ready` returns database `ok`.
6. A read-only leaderboard request and authenticated admin request succeed.

Keep the restored database until the release has passed event rehearsal. Destroying it requires a
separate approved data-retention action.

## 5. Rollback

- If migration fails before application cutover, keep the application on the previous release and
  leave additive columns in place.
- If data integrity fails, stop writes, preserve logs and the original backup, and restore only to
  a separately named database until the incident owner approves a recovery point.
- Never use `git reset`, an ad-hoc destructive SQL script, or a live-database restore as the first
  rollback action.

## 6. Event-day controls

- Run one FastAPI worker unless shared realtime coordination and SQL-backed rate-limit locking have
  passed the staging soak with the planned SQL Server pool settings. The checked-in Render default
  is one worker; change it to two only after the staging evidence is recorded and reviewed.
- Do not restart all API workers during an active buzzer question.
- Monitor readiness, connection pool errors, deadlocks, buzzer 409 rates, answer latency, score
  publication errors, and backup age.
- Keep the previous application image, migration revision, verified backup, and operator contacts
  available before opening the first room.
