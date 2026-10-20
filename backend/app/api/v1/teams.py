from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.db.models import ClassTrack, EventEdition, Round, ScoreEntry, Team, TeamClass
from app.db.session import get_db_session
from app.repositories.team import TeamRepository
from app.schemas.team import (
    ClassTrackResponse,
    EventStandingResponse,
    TeamMemberResponse,
    TeamResponse,
)

router = APIRouter(prefix="/api/v1", tags=["teams"])

ROUND_WEIGHTS = {0: 0.05, 1: 0.10, 2: 0.15, 3: 0.30, 4: 0.40}


@router.get("/classes", response_model=list[ClassTrackResponse])
async def list_classes(
    edition_id: UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[ClassTrackResponse]:
    return await TeamRepository(session).list_classes(edition_id)


@router.get("/teams", response_model=list[TeamResponse])
async def list_teams(
    edition_id: UUID | None = None,
    class_code: str | None = Query(default=None, min_length=1, max_length=8),
    session: AsyncSession = Depends(get_db_session),
) -> list[TeamResponse]:
    if edition_id is None:
        edition_id = await session.scalar(
            select(EventEdition.id)
            .where(EventEdition.status == "ACTIVE")
            .order_by(EventEdition.event_year.desc())
            .limit(1)
        )
    if edition_id is None:
        return []
    teams = await TeamRepository(session).list_public(edition_id, class_code)
    return [
        TeamResponse(
            id=team.id,
            name=team.name,
            slogan=team.slogan,
            team_type=team.team_type,
            members=[
                TeamMemberResponse(
                    student_id=member.student.id,
                    display_name=member.student.display_name,
                    is_public=member.student.is_public,
                )
                for member in team.members
                if member.left_at is None and member.student.is_public
            ],
        )
        for team in teams
    ]


@router.get("/leaderboard", response_model=list[EventStandingResponse])
async def event_leaderboard(session: AsyncSession = Depends(get_db_session)) -> list[EventStandingResponse]:
    edition_id = await session.scalar(
        select(EventEdition.id).where(EventEdition.status == "ACTIVE").order_by(EventEdition.event_year.desc()).limit(1)
    )
    if edition_id is None:
        return []

    teams = (await session.execute(
        select(Team.id, Team.name, ClassTrack.code, Team.registration_order)
        .join(TeamClass, TeamClass.team_id == Team.id)
        .join(ClassTrack, ClassTrack.id == TeamClass.class_track_id)
        .where(Team.event_edition_id == edition_id, Team.is_public)
        .order_by(ClassTrack.code, Team.registration_order, Team.name)
    )).all()
    if not teams:
        return []

    rounds = (await session.execute(
        select(Round.round_number, Round.max_points)
        .where(Round.event_edition_id == edition_id, Round.round_number.in_(ROUND_WEIGHTS))
    )).all()
    maxima = {number: float(max_points) for number, max_points in rounds if max_points and float(max_points) > 0}
    results = (await session.execute(
        select(ScoreEntry.team_id, Round.round_number, func.sum(ScoreEntry.points_delta))
        .join(Round, Round.id == ScoreEntry.round_id)
        .where(ScoreEntry.team_id.in_([row[0] for row in teams]), Round.event_edition_id == edition_id)
        .group_by(ScoreEntry.team_id, Round.round_number)
    )).all()
    points = {(team_id, number): float(value) for team_id, number, value in results}
    scored_team_ids = {team_id for team_id, _ in points}
    active_teams = [row for row in teams if row[0] in scored_team_ids]
    complete_rounds = [
        number for number in ROUND_WEIGHTS if number in maxima
        and all((team_id, number) in points for team_id, _, _, _ in active_teams)
    ]

    weighted: list[tuple[object, str, str, float | None, int, int | None]] = []
    for team_id, name, class_code, registration_order in active_teams:
        weight_total = sum(ROUND_WEIGHTS[number] for number in complete_rounds)
        score = (
            sum(ROUND_WEIGHTS[number] * points[(team_id, number)] / maxima[number] for number in complete_rounds) / weight_total
            if weight_total else None
        )
        weighted.append((team_id, name, class_code, score, len(complete_rounds), registration_order))
    weighted.sort(key=lambda row: (row[3] is None, -(row[3] or 0), row[2], row[5] or 32767, row[1].casefold()))
    return [
        EventStandingResponse(team_id=team_id, team_name=name, class_code=class_code, score=score,
                              completed_rounds=count, is_provisional=count < len(ROUND_WEIGHTS))
        for team_id, name, class_code, score, count, _ in weighted
    ]


@router.get("/admin/teams", response_model=list[TeamResponse])
async def list_admin_teams(
    edition_id: UUID | None = None,
    class_code: str | None = Query(default=None, min_length=1, max_length=8),
    session: AsyncSession = Depends(get_db_session),
    _: dict[str, object] = Depends(require_admin),
) -> list[TeamResponse]:
    if edition_id is None:
        edition_id = await session.scalar(
            select(EventEdition.id)
            .where(EventEdition.status == "ACTIVE")
            .order_by(EventEdition.event_year.desc())
            .limit(1)
        )
    if edition_id is None:
        return []
    teams = await TeamRepository(session).list_admin(edition_id, class_code)
    return [
        TeamResponse(
            id=team.id,
            name=team.name,
            slogan=team.slogan,
            team_type=team.team_type,
            members=[
                TeamMemberResponse(
                    student_id=member.student.id,
                    display_name=member.student.display_name,
                    is_public=member.student.is_public,
                )
                for member in team.members
                if member.left_at is None
            ],
        )
        for team in teams
    ]
