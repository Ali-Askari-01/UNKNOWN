"""Idempotently import the supplied 2026 roster and official Round 0/1 scores.

The workbook files contain student names and must remain outside source control.
Run once without --apply to validate/preview. Apply only after the DB is migrated:
python -m scripts.import_event_scorecard --groups path --scorecard path --apply
"""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import select

from app.db.models import ClassTrack, EventEdition, Round, ScoreEntry, Student, Team, TeamClass, TeamMember
from app.core.config import get_settings
from app.db.session import SessionFactory, dispose_engine, get_schema_revision, initialize_local_database

EVENT_YEAR = 2026
TEAM_RENAMES = {
    ("IX", "Naam Mai Kia Rakha Hai"): "404 Braincells",
    ("IX", "404 braincells"): "404 Braincells",
}
SCORE_REASON = "OFFICIAL_SCORECARD_IMPORT"


def clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def canonical_team_name(class_code: str, name: str) -> str:
    return TEAM_RENAMES.get((class_code, name), name)


def read_group_rows(path: Path) -> list[dict[str, Any]]:
    workbook = load_workbook(path, data_only=True, read_only=True)
    sheet = workbook["Groups"]
    header_row = next(
        (index for index, row in enumerate(sheet.iter_rows(min_row=1, max_row=10, values_only=True), 1)
         if len(row) > 2 and clean(row[0]) == "Class" and clean(row[2]) == "Group Name"),
        None,
    )
    if header_row is None:
        raise ValueError("Groups sheet must have Class and Group Name headers.")
    records = []
    for row in sheet.iter_rows(min_row=header_row + 1, max_row=header_row + 100, max_col=9, values_only=True):
        class_code, order, name, slogan, *members, _ = row
        class_code, name = clean(class_code).upper(), clean(name)
        if class_code not in {"IX", "X", "XI"} or not name:
            continue
        records.append({
            "class_code": class_code,
            "registration_order": int(order),
            "name": canonical_team_name(class_code, name),
            "slogan": clean(slogan) or None,
            "members": [clean(member) for member in members[:4] if clean(member)],
        })
    if not records:
        raise ValueError("No team records found in Groups sheet.")
    if len({(row["class_code"], row["name"].casefold()) for row in records}) != len(records):
        raise ValueError("Duplicate team names found after applying the confirmed rename.")
    return records


def read_score_rows(path: Path) -> dict[tuple[str, str], dict[int, tuple[float, float]]]:
    workbook = load_workbook(path, data_only=True, read_only=True)
    output: dict[tuple[str, str], dict[int, tuple[float, float]]] = defaultdict(dict)
    for class_code, sheet_name in (("IX", "Class IX"), ("X", "Class X"), ("XI", "Class XI")):
        sheet = workbook[sheet_name]
        for row in sheet.iter_rows(min_row=11, max_row=40, max_col=18, values_only=True):
            team_name = clean(row[0])
            if not team_name or team_name == "Group":
                continue
            normalized_name = canonical_team_name(class_code, team_name)
            for round_number, total_index, score_index in ((0, 2, 3), (1, 4, 5)):
                total, score = row[total_index], row[score_index]
                if isinstance(total, (int, float)) and isinstance(score, (int, float)):
                    if total <= 0 or score < 0 or score > total:
                        raise ValueError(f"Invalid score for {class_code}/{normalized_name}, round {round_number}.")
                    output[(class_code, normalized_name)][round_number] = (float(score), float(total))
    return dict(output)


def validate_inputs(groups: list[dict[str, Any]], scores: dict[tuple[str, str], dict[int, tuple[float, float]]]) -> None:
    roster = {(row["class_code"], row["name"]) for row in groups}
    mismatches = sorted(set(scores) - roster)
    missing = sorted(roster - set(scores))
    if mismatches or missing:
        raise ValueError(f"Workbook team mismatch; scorecard-only={mismatches}; roster-only={missing}.")
    for key, rounds in scores.items():
        if set(rounds) != {0, 1}:
            raise ValueError(f"Expected Round 0 and Round 1 marks for {key}.")


async def import_data(groups: list[dict[str, Any]], scores: dict[tuple[str, str], dict[int, tuple[float, float]]], apply: bool) -> None:
    settings = get_settings()
    if settings.database_url.startswith("sqlite+"):
        await initialize_local_database()
    else:
        revision = await get_schema_revision()
        if revision != "0012_team_registration_order":
            raise RuntimeError(f"Database migration is at {revision or 'unknown'}; apply migrations through 0012_team_registration_order first.")

    async with SessionFactory() as session:
        edition = await session.scalar(select(EventEdition).where(EventEdition.event_year == EVENT_YEAR))
        if edition is None:
            raise RuntimeError(f"Event edition {EVENT_YEAR} was not found; import will not create an unapproved event.")
        classes = {
            track.code: track for track in (await session.scalars(
                select(ClassTrack).where(ClassTrack.event_edition_id == edition.id)
            )).all()
        }
        if not {"IX", "X", "XI"}.issubset(classes):
            raise RuntimeError("The 2026 event is missing one or more class tracks IX, X, XI.")

        rounds: dict[int, Round] = {}
        for number, name, maximum in ((0, "Team identity and poster", 10), (1, "Presentation", 15)):
            round_item = await session.scalar(select(Round).where(
                Round.event_edition_id == edition.id, Round.round_number == number
            ))
            if round_item is None:
                round_item = Round(
                    event_edition_id=edition.id, round_number=number, name=name,
                    round_type="OTHER" if number == 0 else "PRESENTATION", status="COMPLETED",
                    description="Imported from the official 2026 event scorecard.", max_points=maximum,
                )
                session.add(round_item)
                await session.flush()
            elif round_item.max_points is not None and float(round_item.max_points) != maximum:
                raise RuntimeError(f"Round {number} already has a conflicting maximum ({round_item.max_points}).")
            else:
                round_item.max_points = maximum
                round_item.status = "COMPLETED"
            rounds[number] = round_item

        team_map: dict[tuple[str, str], Team] = {}
        for data in groups:
            key = (data["class_code"], data["name"])
            team = await session.scalar(select(Team).where(
                Team.event_edition_id == edition.id, Team.name == data["name"]
            ))
            if team is None and (data["class_code"], data["name"]) == ("IX", "404 Braincells"):
                old_team = await session.scalar(select(Team).where(
                    Team.event_edition_id == edition.id, Team.name == "Naam Mai Kia Rakha Hai"
                ))
                if old_team is not None:
                    old_link = await session.scalar(select(TeamClass).where(
                        TeamClass.team_id == old_team.id,
                        TeamClass.class_track_id == classes["IX"].id,
                    ))
                    if old_link is not None:
                        team = old_team
                        team.name = data["name"]
            if team is None:
                team = Team(event_edition_id=edition.id, name=data["name"], slogan=data["slogan"], team_type="LEARNING", is_public=True)
                session.add(team)
                await session.flush()
            else:
                team.name = data["name"]
                team.slogan = data["slogan"]
                team.is_public = True
            team.registration_order = data["registration_order"]
            team_map[key] = team
            class_link = await session.scalar(select(TeamClass).where(
                TeamClass.team_id == team.id, TeamClass.class_track_id == classes[data["class_code"]].id
            ))
            if class_link is None:
                session.add(TeamClass(team_id=team.id, class_track_id=classes[data["class_code"]].id))
            active_members = set((await session.scalars(
                select(Student.display_name)
                .join(TeamMember, TeamMember.student_id == Student.id)
                .where(TeamMember.team_id == team.id, TeamMember.left_at.is_(None))
            )).all())
            for member_index, display_name in enumerate(data["members"], 1):
                if display_name in active_members:
                    continue
                reference = f"TECH26-{data['class_code']}-{data['registration_order']:02d}-{member_index:02d}"
                student = Student(
                    event_edition_id=edition.id,
                    student_reference=reference,
                    display_name=display_name,
                    is_public=True,
                )
                session.add(student)
                await session.flush()
                session.add(TeamMember(team_id=team.id, student_id=student.id, is_captain=False))

        inserted_scores = 0
        for key, round_scores in scores.items():
            team = team_map[key]
            for number, (score, maximum) in round_scores.items():
                if maximum != float(rounds[number].max_points):
                    raise RuntimeError(f"Scorecard maximum does not match configured Round {number} maximum.")
                import_note = f"scorecard-2026-round-{number}"
                round_entries = (await session.scalars(select(ScoreEntry).where(
                    ScoreEntry.team_id == team.id,
                    ScoreEntry.round_id == rounds[number].id,
                ))).all()
                imported = [entry for entry in round_entries if entry.reason == SCORE_REASON and entry.note == import_note]
                if imported:
                    if len(imported) != 1 or len(round_entries) != 1 or float(imported[0].points_delta) != score:
                        raise RuntimeError(f"Conflicting prior import for {key}, round {number}; no data was changed.")
                    continue
                if round_entries:
                    if len(round_entries) != 1 or float(round_entries[0].points_delta) != score:
                        raise RuntimeError(f"Existing score for {key}, round {number} differs from the workbook; refusing to change scores.")
                    # Earlier event-scorecard import already loaded this exact official score.
                    continue
                session.add(ScoreEntry(
                    team_id=team.id, round_id=rounds[number].id, points_delta=score,
                    reason=SCORE_REASON, note=import_note,
                ))
                inserted_scores += 1

        if apply:
            await session.commit()
        else:
            await session.rollback()
        print(f"Mode: {'APPLY' if apply else 'DRY RUN'}; teams: {len(groups)}; rounds: 2; new score entries: {inserted_scores}.")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", required=True, type=Path)
    parser.add_argument("--scorecard", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="Commit the import. Default is validation-only dry run.")
    args = parser.parse_args()
    for path in (args.groups, args.scorecard):
        if not path.is_file():
            raise SystemExit(f"Input workbook not found: {path}")
    groups = read_group_rows(args.groups)
    scores = read_score_rows(args.scorecard)
    validate_inputs(groups, scores)
    await import_data(groups, scores, args.apply)
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
