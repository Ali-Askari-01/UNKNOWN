# Database Testing and Acceptance Plan

## Automated tests

- Migration applies from an empty SQL Server database.
- Migration is repeatable through the migration ledger and checksum validation.
- All foreign keys, unique constraints, checks, and filtered indexes reject invalid cases.
- Seed scripts are idempotent.
- Repository CRUD tests cover every entity used by the API.
- Transaction tests prove answer judgment and score entry commit or roll back together.
- Concurrent buzzer tests prove one winner per quiz question.
- Question selection tests prove class/language/type/difficulty eligibility and distribution totals.
- Public query tests prove private fields and answer keys are absent.
- Backup restore test proves the application can read restored event history.

## Data quality checks

- No team without an event edition.
- No active team member without a student.
- No question lacking a valid answer policy.
- No published quiz session without selected questions.
- No score entry without a team and round.
- No public media that is not approved.
- No event edition with duplicate class codes or round numbers.

## Performance tests

- Load question selection and leaderboard queries with projected multi-year data.
- Simulate the expected number of connected teams and simultaneous buzzer presses.
- Measure p95 API latency, websocket broadcast latency, database CPU, locks, and pool usage.
- Test reconnects and duplicate requests with idempotency keys.
