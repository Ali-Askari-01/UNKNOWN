# 2026 roster and scorecard import

The source workbooks are private working files and are intentionally not stored in this repository.
The import command reads the roster and scorecard from local paths, validates all 14 teams and their
Round 0/1 marks, then upserts the 2026 event teams and players. It preserves team source order, uses
stable non-sensitive student references, and never overwrites or duplicates an existing score.

Install the backend development extra (which includes `openpyxl`) and first apply the reviewed
database migrations through `0012_team_registration_order`:

```powershell
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m scripts.import_event_scorecard `
  --groups "C:\path\to\class_groups.xlsx" `
  --scorecard "C:\path\to\TECH_EVENT_SCORECARD_proper_ranking.xlsx"
```

The command is validation-only by default. Add `--apply` to commit. Re-running it is safe. If an
existing Round 0/1 score differs from the workbook, it stops rather than changing or double-counting
that ledger entry. The confirmed Class IX rename maps the roster's former second-team name to
`404 Braincells` while keeping its team record and members.

The public class pages and admin team view read player/team records from the database. The event
leaderboard calculates the weighted normalized score from complete rounds only, using weights 5%,
10%, 15%, 30%, and 40% for Rounds 0–4. It keeps the workbook's source order for ties and marks
standings provisional until all five rounds are complete. Round maxima must be configured before a
round can contribute to the overall ranking.
