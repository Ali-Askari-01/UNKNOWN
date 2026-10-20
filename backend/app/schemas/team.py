from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClassTrackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    display_name: str
    preferred_language: str


class TeamMemberResponse(BaseModel):
    student_id: UUID
    display_name: str
    is_public: bool


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slogan: str | None
    team_type: str
    members: list[TeamMemberResponse]


class EventStandingResponse(BaseModel):
    team_id: UUID
    team_name: str
    class_code: str
    score: float | None
    completed_rounds: int
    is_provisional: bool
