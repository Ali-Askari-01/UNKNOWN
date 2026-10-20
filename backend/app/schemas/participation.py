from uuid import UUID

from pydantic import BaseModel, Field


class ParticipantCreate(BaseModel):
    team_id: UUID


class TeamJoinRequest(BaseModel):
    quiz_code: str = Field(min_length=4, max_length=32)
    team_id: UUID


class ParticipantResponse(BaseModel):
    id: UUID
    quiz_session_id: UUID
    team_id: UUID


class TeamJoinResponse(ParticipantResponse):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 8 * 60 * 60


class AnswerCreate(BaseModel):
    participant_id: UUID
    quiz_question_id: UUID
    submitted_answer: str = Field(min_length=1, max_length=5000)


class AnswerResponse(BaseModel):
    id: UUID
    quiz_question_id: UUID
    is_correct: bool | None
    awarded_points: int


class JudgeAnswerRequest(BaseModel):
    is_correct: bool
    awarded_points: int | None = Field(default=None, ge=-100, le=100)


class AdminAnswerResponse(BaseModel):
    id: UUID
    quiz_question_id: UUID
    question_order: int
    team_name: str
    submitted_answer: str
    is_correct: bool | None
    awarded_points: int
    submitted_at: str


class BuzzerResponse(BaseModel):
    id: UUID
    quiz_question_id: UUID
    participant_id: UUID
    team_name: str
    is_winner: bool
    answer_deadline: str


class LeaderboardEntry(BaseModel):
    team_id: UUID
    team_name: str
    points: int
