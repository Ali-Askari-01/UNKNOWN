# Database Migration, Seeding, and Rollout Plan

## Migration rules

- Every migration has a monotonically increasing ID, description, author, and checksum.
- Migrations are reviewed in pull requests and executed automatically in staging.
- Production migration requires a backup, maintenance window decision, and smoke test.
- Destructive changes use expand/migrate/contract steps; never drop a live column in the same release that stops writing it.
- Seed data is idempotent and uses stable business keys such as event year, class code, role code, and tag code.

## Initial migration sequence

1. Create `competition` schema and migration ledger.
2. Create event, identity, class, team, student, and media tables.
3. Create rounds, question bank, submissions, quiz, answer, score, and audit tables.
4. Add indexes, filtered uniqueness, checks, and foreign keys.
5. Insert roles and controlled vocabularies.
6. Seed one DRAFT event edition and IX/X/XI class tracks.
7. Import verified teams and members from the current `data/event.ts` only after staff review.
8. Import questions through a staging table and validate every option/answer/category.
9. Publish the edition only after operator acceptance.

## Safe question import

Use JSON/CSV staging with columns: external key, class codes, type, difficulty, language, prompt, code snippet, options, correct option, explanation, points, tags. Reject rows with missing answer keys, duplicate external keys, invalid class codes, unsupported types, or distribution-incompatible metadata. Never import an answer key into a client bundle.

## Rollback strategy

- Application rollback is independent from database rollback whenever possible.
- For additive migrations, roll back application code first and leave compatible columns.
- For data fixes, use compensating scripts with before/after counts.
- Restore a backup only after determining whether corruption is logical or physical.
- Record migration version and application release in deployment metadata.

## Environment matrix

| Environment | Purpose | Data policy |
|---|---|---|
| Local | Developer workflow | Synthetic/demo data only |
| CI | Migration and tests | Ephemeral database, no secrets |
| Staging | Full rehearsal | Masked copy or generated data |
| Production | Live event | Real data, restricted access, backups |
