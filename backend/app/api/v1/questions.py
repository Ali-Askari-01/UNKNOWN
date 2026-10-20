import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.core.auth import require_admin
from app.core.audit import add_audit
from app.db.models import ClassTrack, Question, QuestionClass, QuestionOption
from app.db.session import get_db_session
from app.schemas.question import (
    QuestionAdmin,
    QuestionActivation,
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
        accepted_answers=json.loads(question.accepted_answers or "[]"),
        is_active=question.is_active,
        class_track_ids=[link.class_track_id for link in question.class_links],
        options=[QuestionOptionAdmin(key=o.option_key, text=o.option_text, is_correct=o.is_correct) for o in sorted(question.options, key=lambda item: item.sort_order)],
    )


def question_query(include_inactive: bool = False):
    query = select(Question).options(selectinload(Question.options), selectinload(Question.class_links))
    if not include_inactive:
        query = query.where(Question.is_active)
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
    class_count = await session.scalar(select(func.count(ClassTrack.id)).where(ClassTrack.id.in_(payload.class_track_ids)))
    if class_count != len(set(payload.class_track_ids)):
        raise AppError("INVALID_CLASS_TRACK", "Every selected class track must exist.")

    question = Question(
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        preferred_language=payload.preferred_language,
        prompt=payload.prompt,
        code_snippet=payload.code_snippet,
        explanation=payload.explanation,
        accepted_answers=json.dumps(payload.accepted_answers, ensure_ascii=False),
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


@router.put("/admin/questions/{question_id}", response_model=QuestionAdmin)
async def update_question(
    question_id: UUID,
    payload: QuestionCreate,
    session: AsyncSession = Depends(get_db_session),
    admin: dict[str, object] = Depends(require_admin),
) -> QuestionAdmin:
    question = await session.scalar(
        select(Question)
        .options(selectinload(Question.options), selectinload(Question.class_links))
        .where(Question.id == question_id)
    )
    if question is None:
        raise AppError("QUESTION_NOT_FOUND", "The question was not found.", 404)

    class_count = await session.scalar(select(func.count(ClassTrack.id)).where(ClassTrack.id.in_(payload.class_track_ids)))
    if class_count != len(set(payload.class_track_ids)):
        raise AppError("INVALID_CLASS_TRACK", "Every selected class track must exist.")

    question.question_type = payload.question_type
    question.difficulty = payload.difficulty
    question.preferred_language = payload.preferred_language
    question.prompt = payload.prompt
    question.code_snippet = payload.code_snippet
    question.explanation = payload.explanation
    question.accepted_answers = json.dumps(payload.accepted_answers, ensure_ascii=False)
    question.default_points = payload.default_points
    question.updated_at = datetime.now(timezone.utc)
    question.options = [
        QuestionOption(option_key=option.key, option_text=option.text, is_correct=option.is_correct, sort_order=index)
        for index, option in enumerate(payload.options)
    ]
    question.class_links = [QuestionClass(class_track_id=class_id) for class_id in payload.class_track_ids]
    add_audit(
        session,
        action_code="QUESTION_UPDATED",
        entity_name="question",
        entity_id=question.id,
        details={
            "fields": [
                "question_type", "difficulty", "preferred_language", "prompt", "code_snippet",
                "explanation", "default_points", "class_track_ids", "options",
            ],
            "actor": admin.get("sub"),
        },
    )
    await session.commit()
    updated = await session.scalar(
        select(Question)
        .options(selectinload(Question.options), selectinload(Question.class_links))
        .where(Question.id == question_id)
    )
    assert updated is not None
    return to_admin(updated)


@router.patch("/admin/questions/{question_id}/active", response_model=QuestionAdmin)
async def set_question_active(
    question_id: UUID,
    payload: QuestionActivation,
    session: AsyncSession = Depends(get_db_session),
    admin: dict[str, object] = Depends(require_admin),
) -> QuestionAdmin:
    question = await session.scalar(
        select(Question)
        .options(selectinload(Question.options), selectinload(Question.class_links))
        .where(Question.id == question_id)
    )
    if question is None:
        raise AppError("QUESTION_NOT_FOUND", "The question was not found.", 404)
    if question.is_active != payload.is_active:
        question.is_active = payload.is_active
        question.updated_at = datetime.now(timezone.utc)
        add_audit(
            session,
            action_code="QUESTION_ACTIVATED" if question.is_active else "QUESTION_RETIRED",
            entity_name="question",
            entity_id=question.id,
            details={"actor": admin.get("sub")},
        )
        await session.commit()
    return to_admin(question)
