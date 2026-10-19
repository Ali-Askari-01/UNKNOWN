from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.core.auth import require_admin
from app.core.audit import add_audit
from app.db.models import ClassTrack, Question, QuestionClass, QuestionOption
from app.db.session import get_db_session
from app.schemas.question import (
    QuestionAdmin,
    QuestionCreate,
    QuestionOptionAdmin,
    QuestionOptionPublic,
    QuestionPublic,
)

router = APIRouter(prefix="/api/v1", tags=["questions"])


def to_public(question: Question) -> QuestionPublic:
    return QuestionPublic(
        id=question.id,
        question_type=question.question_type,
        difficulty=question.difficulty,
        preferred_language=question.preferred_language,
        prompt=question.prompt,
        code_snippet=question.code_snippet,
        default_points=question.default_points,
        options=[QuestionOptionPublic(key=o.option_key, text=o.option_text) for o in sorted(question.options, key=lambda item: item.sort_order)],
    )


def to_admin(question: Question) -> QuestionAdmin:
    public = to_public(question).model_dump()
    public.pop("options", None)
    return QuestionAdmin(
        **public,
        explanation=question.explanation,
        is_active=question.is_active,
        class_track_ids=[link.class_track_id for link in question.class_links],
        options=[QuestionOptionAdmin(key=o.option_key, text=o.option_text, is_correct=o.is_correct) for o in sorted(question.options, key=lambda item: item.sort_order)],
    )


def question_query(include_inactive: bool = False):
    query = select(Question).options(selectinload(Question.options), selectinload(Question.class_links))
    if not include_inactive:
        query = query.where(Question.is_active == True)
    return query.order_by(Question.created_at.desc())


@router.get("/questions", response_model=list[QuestionPublic])
async def list_public_questions(
    class_code: str | None = Query(default=None, min_length=1, max_length=8),
    question_type: str | None = Query(default=None, max_length=30),
    difficulty: str | None = Query(default=None, max_length=20),
    session: AsyncSession = Depends(get_db_session),
) -> list[QuestionPublic]:
    query = question_query()
    if class_code:
        query = query.join(QuestionClass).join(ClassTrack).where(ClassTrack.code == class_code.upper())
    if question_type:
        query = query.where(Question.question_type == question_type.upper())
    if difficulty:
        query = query.where(Question.difficulty == difficulty.upper())
    questions = (await session.scalars(query)).unique().all()
    return [to_public(question) for question in questions]


@router.get("/admin/questions", response_model=list[QuestionAdmin])
async def list_admin_questions(session: AsyncSession = Depends(get_db_session), _: dict[str, object] = Depends(require_admin)) -> list[QuestionAdmin]:
    questions = (await session.scalars(question_query(include_inactive=True))).unique().all()
    return [to_admin(question) for question in questions]


@router.post("/admin/questions", response_model=QuestionAdmin, status_code=201)
async def create_question(payload: QuestionCreate, session: AsyncSession = Depends(get_db_session), _: dict[str, object] = Depends(require_admin)) -> QuestionAdmin:
    class_count = await session.scalar(select(ClassTrack.id).where(ClassTrack.id.in_(payload.class_track_ids)).limit(1))
    if class_count is None:
        raise AppError("INVALID_CLASS_TRACK", "At least one class track must exist.")

    question = Question(
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        preferred_language=payload.preferred_language,
        prompt=payload.prompt,
        code_snippet=payload.code_snippet,
        explanation=payload.explanation,
        default_points=payload.default_points,
    )
    question.options = [QuestionOption(option_key=o.key, option_text=o.text, is_correct=o.is_correct, sort_order=index) for index, o in enumerate(payload.options)]
    question.class_links = [QuestionClass(class_track_id=class_id) for class_id in payload.class_track_ids]
    session.add(question)
    await session.flush()
    add_audit(session, action_code="QUESTION_CREATED", entity_name="question", entity_id=question.id, details={"question_type": question.question_type})
    await session.commit()
    await session.refresh(question)
    return to_admin(question)
