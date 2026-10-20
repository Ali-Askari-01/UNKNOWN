from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ClassTrack, Team, TeamClass, TeamMember


class TeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_classes(self, edition_id: UUID | None = None) -> list[ClassTrack]:
        query = select(ClassTrack).order_by(ClassTrack.code)
        if edition_id is not None:
            query = query.where(ClassTrack.event_edition_id == edition_id)
        return list((await self.session.scalars(query)).all())

    async def list_public(self, edition_id: UUID, class_code: str | None = None) -> list[Team]:
        query = (
            select(Team)
            .options(selectinload(Team.members).selectinload(TeamMember.student))
            .where(Team.event_edition_id == edition_id, Team.is_public)
            .order_by(Team.registration_order, Team.name)
        )
        if class_code is not None:
            query = query.join(TeamClass).join(ClassTrack).where(ClassTrack.code == class_code)
        return list((await self.session.scalars(query)).unique().all())

    async def list_admin(self, edition_id: UUID, class_code: str | None = None) -> list[Team]:
        query = (
            select(Team)
            .options(selectinload(Team.members).selectinload(TeamMember.student))
            .where(Team.event_edition_id == edition_id)
            .order_by(Team.registration_order, Team.name)
        )
        if class_code is not None:
            query = query.join(TeamClass).join(ClassTrack).where(ClassTrack.code == class_code)
        return list((await self.session.scalars(query)).unique().all())
