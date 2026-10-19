from uuid import UUID

from pydantic import BaseModel, Field


class ParticipantCreate(BaseModel):
    team_id: UUID


class ParticipantResponse(BaseModel):
    id: UUID
    quiz_session_id: UUID
    team_id: UUID


class AnswerCreate(BaseModel):
    participant_id: UUID
    quiz_question_id: UUID
    submitted_answer: str = Field(min_length=1, max_length=5000)


class AnswerResponse(BaseModel):
    id: UUID
    quiz_question_id: UUID
    is_correct: bool
    awarded_points: int


class LeaderboardEntry(BaseModel):
    team_id: UUID
    team_name: str
    points: int
