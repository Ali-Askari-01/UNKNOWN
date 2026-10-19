from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventEdition
from app.db.session import get_db_session
from app.repositories.team import TeamRepository
from app.schemas.team import ClassTrackResponse, TeamMemberResponse, TeamResponse

router = APIRouter(prefix="/api/v1", tags=["teams"])


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
