# Database Requirements and Rules

## Scope

SQL Server is the system of record for event editions, classes, students, teams, media metadata, rounds, question bank, quiz execution, submissions, scoring, users, and audit history.

## Data ownership

- Event edition owns the annual lifecycle.
- Class track owns IX/X/XI configuration for one edition.
- Student is the person record; team membership is a separate dated relationship.
- Team is the competition unit; `LEARNING` and `MIXED` teams are both supported.
- Question is reusable content; quiz question is the historical session snapshot.
- Score entry is an append-only fact; leaderboard is derived.
- Media asset is metadata only; binary data lives in object storage.

## Integrity rules

1. Every edition-scoped record carries an edition relationship directly or through a required parent.
2. All external IDs are opaque UUIDs; no sequential IDs are exposed to browsers.
3. All timestamps are UTC `datetime2(3)`.
4. Names and display text are Unicode `nvarchar`.
5. Delete behavior is explicit. Historical quiz/session/score data is never cascaded away.
6. Question options and answer keys are protected from public serializers.
7. Score corrections create a new compensating row instead of editing history.
8. A quiz session snapshots selected question text, points, and answer key at selection time.
9. A quiz blueprint cannot start until its distribution total equals its question count and every bucket has enough eligible questions.
10. Public media must be approved and public; private or pending media is never returned by public endpoints.

## Transaction boundaries

- Create/update team plus membership changes: one transaction.
- Start quiz and select/snapshot questions: one transaction with a deterministic seed recorded for support.
- Accept winning buzzer: one transaction/serialized critical section with a filtered unique winner index.
- Judge answer and create score entry: one transaction.
- Publish result: one transaction that changes publication state and writes audit data.

## Retention

- Keep event, round, quiz, answer, and score history for future reporting.
- Keep audit logs according to institutional policy; recommended minimum is seven years for event decisions.
- Store media retention and consent expiry explicitly; deletion must produce an audit event.
