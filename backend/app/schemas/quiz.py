from uuid import UUID

from pydantic import BaseModel, Field, model_validator

QUESTION_TYPES = "MCQ|RIDDLE|CODE|DEBUGGING|CONCEPTUAL|THEORY"


class QuizDistributionInput(BaseModel):
    question_type: str = Field(pattern=f"^({QUESTION_TYPES})$")
    difficulty: str | None = Field(default=None, pattern="^(EASY|MEDIUM|HARD)$")
    quantity: int = Field(ge=1, le=500)


class QuizBlueprintCreate(BaseModel):
    round_id: UUID
    class_track_id: UUID
    name: str = Field(min_length=1, max_length=160)
    question_count: int = Field(ge=1, le=500)
    seconds_per_question: int = Field(default=20, ge=1, le=3600)
    buzzer_enabled: bool = True
    distributions: list[QuizDistributionInput] = Field(min_length=1)

    @model_validator(mode="after")
    def distribution_total_matches_count(self) -> "QuizBlueprintCreate":
        if sum(item.quantity for item in self.distributions) != self.question_count:
            raise ValueError("Distribution quantities must add up to question_count.")
        return self


class QuizDistributionResponse(QuizDistributionInput):
    id: UUID


class QuizBlueprintResponse(BaseModel):
    id: UUID
    round_id: UUID
    class_track_id: UUID
    name: str
    question_count: int
    seconds_per_question: int
    buzzer_enabled: bool
    is_active: bool
    distributions: list[QuizDistributionResponse]
