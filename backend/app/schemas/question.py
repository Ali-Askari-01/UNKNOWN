from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class QuestionOptionInput(BaseModel):
    key: str = Field(min_length=1, max_length=10)
    text: str = Field(min_length=1, max_length=500)
    is_correct: bool = False


class QuestionCreate(BaseModel):
    question_type: str = Field(pattern="^(MCQ|RIDDLE|CODE|DEBUGGING|CONCEPTUAL|THEORY)$")
    difficulty: str = Field(pattern="^(EASY|MEDIUM|HARD)$")
    preferred_language: str | None = Field(default=None, max_length=40)
    prompt: str = Field(min_length=1)
    code_snippet: str | None = None
    explanation: str | None = None
    accepted_answers: list[str] = Field(default_factory=list, max_length=20)
    default_points: int = Field(default=10, ge=1, le=100)
    class_track_ids: list[UUID] = Field(min_length=1)
    options: list[QuestionOptionInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_options(self) -> "QuestionCreate":
        if self.question_type == "MCQ":
            if len(self.options) < 2 or sum(option.is_correct for option in self.options) != 1:
                raise ValueError("MCQ questions require at least two options and exactly one correct option.")
        elif self.options:
            raise ValueError("Only MCQ questions may contain options.")
        if self.question_type != "MCQ" and not any(answer.strip() for answer in self.accepted_answers):
            raise ValueError("Non-MCQ questions require at least one accepted answer for automatic grading.")
        self.accepted_answers = list(dict.fromkeys(answer.strip() for answer in self.accepted_answers if answer.strip()))
        return self


class QuestionActivation(BaseModel):
    is_active: bool


class QuestionOptionPublic(BaseModel):
    key: str
    text: str


class QuestionPublic(BaseModel):
    id: UUID
    question_type: str
    difficulty: str
    preferred_language: str | None
    prompt: str
    code_snippet: str | None
    default_points: int
    options: list[QuestionOptionPublic]


class QuestionOptionAdmin(QuestionOptionPublic):
    is_correct: bool


class QuestionAdmin(QuestionPublic):
    explanation: str | None
    accepted_answers: list[str]
    is_active: bool
    class_track_ids: list[UUID]
    options: list[QuestionOptionAdmin]
