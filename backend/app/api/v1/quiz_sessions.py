import json
import secrets
import string
from random import SystemRandom
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.core.auth import require_admin
from app.core.audit import add_audit
from app.db.models import ClassTrack, Question, QuestionClass, QuizBlueprint, QuizQuestion, QuizSession
from app.db.session import get_db_session
from app.schemas.session import QuizSessionCreate, QuizSessionJoinResponse, QuizSessionQuestionAdmin, QuizSessionQuestionPublic, QuizSessionResponse

router = APIRouter(prefix="/api/v1", tags=["quiz-sessions"])
randomizer = SystemRandom()


def make_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))


def session_response(session: QuizSession, question_count: int | None = None) -> QuizSessionResponse:
    return QuizSessionResponse(
        id=session.id,
        blueprint_id=session.blueprint_id,
        quiz_code=session.quiz_code,
        status=session.status,
        question_count=question_count if question_count is not None else len(session.questions),
    )


def question_public(item: QuizQuestion) -> QuizSessionQuestionPublic:
    question = item.question
    options = json.loads(item.answer_key_snapshot or "[]")
    return QuizSessionQuestionPublic(
        id=item.id,
        question_order=item.question_order,
        prompt=item.prompt_snapshot,
        code_snippet=item.question.code_snippet,
        options=[{"key": option["key"], "text": option["text"]} for option in options],
    )


def question_admin(item: QuizQuestion) -> QuizSessionQuestionAdmin:
    public = question_public(item)
    return QuizSessionQuestionAdmin(**public.model_dump(), answer_key=item.answer_key_snapshot)


async def load_blueprint(session: AsyncSession, blueprint_id: UUID) -> tuple[QuizBlueprint, ClassTrack]:
    blueprint = await session.scalar(
        select(QuizBlueprint)
        .options(selectinload(QuizBlueprint.distributions))
        .where(QuizBlueprint.id == blueprint_id, QuizBlueprint.is_active == True)
    )
    if blueprint is None:
        raise AppError("BLUEPRINT_NOT_FOUND", "The active quiz blueprint was not found.", 404)
    class_track = await session.scalar(select(ClassTrack).where(ClassTrack.id == blueprint.class_track_id))
    if class_track is None:
        raise AppError("CLASS_TRACK_NOT_FOUND", "The blueprint class track was not found.", 404)
    return blueprint, class_track


@router.post("/admin/quiz-sessions", response_model=QuizSessionResponse, status_code=201)
async def create_quiz_session(payload: QuizSessionCreate, session: AsyncSession = Depends(get_db_session), _: dict[str, object] = Depends(require_admin)) -> QuizSessionResponse:
    blueprint, class_track = await load_blueprint(session, payload.blueprint_id)
    selected: list[Question] = []
    selected_ids: set[UUID] = set()

    for distribution in blueprint.distributions:
        query = (
            select(Question)
            .options(selectinload(Question.options))
            .join(QuestionClass)
            .where(
                Question.is_active == True,
                Question.question_type == distribution.question_type,
                QuestionClass.class_track_id == class_track.id,
            )
        )
        if distribution.difficulty is not None:
            query = query.where(Question.difficulty == distribution.difficulty)
        if class_track.preferred_language:
            query = query.where(
                (Question.preferred_language.is_(None))
                | (Question.preferred_language == class_track.preferred_language)
            )
        candidates = [item for item in (await session.scalars(query)).unique().all() if item.id not in selected_ids]
        if len(candidates) < distribution.quantity:
            raise AppError(
                "INSUFFICIENT_QUESTION_BANK",
                f"Need {distribution.quantity} {distribution.question_type} question(s), but only {len(candidates)} eligible question(s) are available for Class {class_track.code}.",
                409,
            )
        chosen = randomizer.sample(candidates, distribution.quantity)
        selected.extend(chosen)
        selected_ids.update(item.id for item in chosen)

    randomizer.shuffle(selected)
    quiz_session = QuizSession(blueprint_id=blueprint.id, quiz_code=make_code(), status="WAITING")
    quiz_session.questions = []
    for order, question in enumerate(selected, start=1):
        answer_options = [
            {"key": option.option_key, "text": option.option_text, "is_correct": option.is_correct}
            for option in sorted(question.options, key=lambda item: item.sort_order)
        ]
        quiz_session.questions.append(
            QuizQuestion(
                question_id=question.id,
                question_order=order,
                prompt_snapshot=question.prompt,
                points_snapshot=question.default_points,
                answer_key_snapshot=json.dumps(answer_options),
            )
        )
    session.add(quiz_session)
    await session.flush()
    add_audit(session, action_code="QUIZ_SESSION_CREATED", entity_name="quiz_session", entity_id=quiz_session.id, details={"question_count": len(selected)})
    await session.commit()
    await session.refresh(quiz_session)
    return session_response(quiz_session, len(selected))


@router.get("/quiz-sessions/{session_id}/questions", response_model=list[QuizSessionQuestionPublic])
async def list_session_questions(session_id: UUID, session: AsyncSession = Depends(get_db_session)) -> list[QuizSessionQuestionPublic]:
    items = (await session.scalars(select(QuizQuestion).options(selectinload(QuizQuestion.question)).where(QuizQuestion.quiz_session_id == session_id).order_by(QuizQuestion.question_order))).all()
    if not items:
        raise AppError("SESSION_NOT_FOUND", "The quiz session or its questions were not found.", 404)
    return [question_public(item) for item in items]


@router.get("/quiz-sessions/by-code/{quiz_code}", response_model=QuizSessionJoinResponse)
async def find_session_by_code(quiz_code: str, session: AsyncSession = Depends(get_db_session)) -> QuizSessionJoinResponse:
    result = await session.execute(
        select(QuizSession, QuizBlueprint, ClassTrack)
        .join(QuizBlueprint, QuizBlueprint.id == QuizSession.blueprint_id)
        .join(ClassTrack, ClassTrack.id == QuizBlueprint.class_track_id)
        .where(QuizSession.quiz_code == quiz_code.strip().upper())
    )
    row = result.first()
    if row is None:
        raise AppError("SESSION_NOT_FOUND", "The quiz code was not found.", 404)
    quiz_session, _, class_track = row
    question_count = await session.scalar(
        select(func.count(QuizQuestion.id)).where(QuizQuestion.quiz_session_id == quiz_session.id)
    )
    return QuizSessionJoinResponse(
        id=quiz_session.id,
        blueprint_id=quiz_session.blueprint_id,
        quiz_code=quiz_session.quiz_code,
        status=quiz_session.status,
        question_count=int(question_count or 0),
        class_code=class_track.code,
    )


@router.get("/admin/quiz-sessions/{session_id}/questions", response_model=list[QuizSessionQuestionAdmin])
async def list_admin_session_questions(session_id: UUID, session: AsyncSession = Depends(get_db_session), _: dict[str, object] = Depends(require_admin)) -> list[QuizSessionQuestionAdmin]:
    items = (await session.scalars(select(QuizQuestion).options(selectinload(QuizQuestion.question)).where(QuizQuestion.quiz_session_id == session_id).order_by(QuizQuestion.question_order))).all()
    if not items:
        raise AppError("SESSION_NOT_FOUND", "The quiz session or its questions were not found.", 404)
    return [question_admin(item) for item in items]
