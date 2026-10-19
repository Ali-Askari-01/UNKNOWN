from uuid import UUID

from pydantic import BaseModel, Field


class QuizSessionCreate(BaseModel):
    blueprint_id: UUID


class QuizSessionResponse(BaseModel):
    id: UUID
    blueprint_id: UUID
    quiz_code: str
    status: str
    question_count: int


class QuizSessionJoinResponse(QuizSessionResponse):
    class_code: str


class QuizSessionQuestionPublic(BaseModel):
    id: UUID
    question_order: int
    prompt: str
    code_snippet: str | None
    options: list[dict[str, str]]


class QuizSessionQuestionAdmin(QuizSessionQuestionPublic):
    answer_key: str | None
