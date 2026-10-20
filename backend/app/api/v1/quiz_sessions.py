import json
import secrets
import string
from datetime import datetime, timezone
from random import SystemRandom
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.core.auth import require_admin
from app.core.audit import add_audit
from app.core.idempotency import request_hash, reserve
from app.db.models import ClassTrack, Question, QuestionClass, QuizBlueprint, QuizQuestion, QuizSession
from app.db.session import get_db_session
from app.realtime.manager import connection_manager
from app.schemas.session import QuizSessionActionResponse, QuizSessionCreate, QuizSessionJoinResponse, QuizSessionQuestionAdmin, QuizSessionQuestionPublic, QuizSessionResponse

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
    options = json.loads(item.answer_key_snapshot or "[]")
    return QuizSessionQuestionPublic(
        id=item.id,
        question_order=item.question_order,
        prompt=item.prompt_snapshot,
        question_type=item.question_type_snapshot,
        code_snippet=item.code_snippet_snapshot,
        options=[{"key": option["key"], "text": option["text"]} for option in options],
    )


def question_admin(item: QuizQuestion) -> QuizSessionQuestionAdmin:
    public = question_public(item)
    return QuizSessionQuestionAdmin(**public.model_dump(), answer_key=item.answer_key_snapshot)


async def load_blueprint(session: AsyncSession, blueprint_id: UUID) -> tuple[QuizBlueprint, ClassTrack]:
    blueprint = await session.scalar(
        select(QuizBlueprint)
        .options(selectinload(QuizBlueprint.distributions))
        .where(QuizBlueprint.id == blueprint_id, QuizBlueprint.is_active)
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
    distribution_total = sum(item.quantity for item in blueprint.distributions)
    if distribution_total != blueprint.question_count:
        raise AppError(
            "INVALID_BLUEPRINT_DISTRIBUTION",
            f"This blueprint specifies {blueprint.question_count} questions, but its category quantities add up to {distribution_total}.",
            409,
        )
    selected: list[Question] = []
    selected_ids: set[UUID] = set()

    for distribution in blueprint.distributions:
        query = (
            select(Question)
            .options(selectinload(Question.options))
            .join(QuestionClass)
            .where(
                Question.is_active,
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

    if len(selected) != blueprint.question_count:
        raise AppError("QUIZ_QUESTION_COUNT_MISMATCH", "The session could not be created with the blueprint's full question count.", 409)

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
                code_snippet_snapshot=question.code_snippet,
                question_type_snapshot=question.question_type,
                accepted_answers_snapshot=question.accepted_answers,
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


@router.get("/admin/quiz-sessions", response_model=list[QuizSessionResponse])
async def list_admin_quiz_sessions(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    _: dict[str, object] = Depends(require_admin),
) -> list[QuizSessionResponse]:
    sessions = (
        await session.scalars(
            select(QuizSession)
            .options(selectinload(QuizSession.questions))
            .order_by(QuizSession.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return [session_response(item, len(item.questions)) for item in sessions]


@router.post("/admin/quiz-sessions/{session_id}/actions/{action}", response_model=QuizSessionActionResponse)
async def quiz_session_action(
    session_id: UUID,
    action: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin_identity: dict[str, object] = Depends(require_admin),
) -> QuizSessionActionResponse:
    allowed_actions = {"open", "start", "pause", "resume", "advance", "end"}
    if action not in allowed_actions:
        raise AppError("UNKNOWN_SESSION_ACTION", "The requested quiz session action is not supported.", 400)

    quiz_session = await session.scalar(
        select(QuizSession).options(selectinload(QuizSession.questions)).where(QuizSession.id == session_id)
    )
    if quiz_session is None:
        raise AppError("SESSION_NOT_FOUND", "The quiz session was not found.", 404)

    idempotency_record = await reserve(
        session,
        scope_key=f"session-action:{session_id}:{action}:{admin_identity.get('sub')}",
        key=request.headers.get("Idempotency-Key"),
        payload_hash=request_hash({"action": action, "session_id": str(session_id)}),
    )
    if idempotency_record is not None and idempotency_record.response_json:
        return QuizSessionActionResponse.model_validate_json(idempotency_record.response_json)

    expected_version = quiz_session.version_id
    version_update = await session.execute(
        update(QuizSession)
        .where(QuizSession.id == session_id, QuizSession.version_id == expected_version)
        .values(version_id=expected_version + 1)
        .execution_options(synchronize_session=False)
    )
    if version_update.rowcount != 1:
        await session.rollback()
        raise AppError(
            "SESSION_STATE_CHANGED",
            "Another administrator changed this quiz session. Refresh its state and retry.",
            409,
        )

    transitions = {
        "open": {"WAITING": "OPEN"},
        "start": {"OPEN": "ACTIVE"},
        "pause": {"ACTIVE": "PAUSED"},
        "resume": {"PAUSED": "ACTIVE"},
        "advance": {"ACTIVE": "ACTIVE"},
        "end": {"WAITING": "ENDED", "OPEN": "ENDED", "ACTIVE": "ENDED", "PAUSED": "ENDED"},
    }
    if action != "advance" and quiz_session.status not in transitions[action]:
        raise AppError("INVALID_SESSION_TRANSITION", f"Cannot {action} a session in {quiz_session.status} state.", 409)
    if action == "advance" and quiz_session.status != "ACTIVE":
        raise AppError("INVALID_SESSION_TRANSITION", "Only an active session can advance.", 409)

    now = datetime.now(timezone.utc)
    current = next((item for item in quiz_session.questions if item.opened_at is not None and item.closed_at is None), None)
    if action == "open":
        quiz_session.status = "OPEN"
    elif action == "start":
        quiz_session.status = "ACTIVE"
        quiz_session.started_at = now
        current = min(quiz_session.questions, key=lambda item: item.question_order, default=None)
        if current is not None:
            current.opened_at = now
    elif action == "pause":
        quiz_session.status = "PAUSED"
    elif action == "resume":
        quiz_session.status = "ACTIVE"
    elif action == "advance":
        if current is not None:
            current.closed_at = now
        current = next(
            (item for item in sorted(quiz_session.questions, key=lambda item: item.question_order) if item.opened_at is None),
            None,
        )
        if current is None:
            quiz_session.status = "ENDED"
            quiz_session.ended_at = now
        else:
            current.opened_at = now
    elif action == "end":
        quiz_session.status = "ENDED"
        quiz_session.ended_at = now
        if current is not None:
            current.closed_at = now

    add_audit(
        session,
        action_code=f"QUIZ_SESSION_{action.upper()}",
        entity_name="quiz_session",
        entity_id=quiz_session.id,
        details={"status": quiz_session.status, "question_order": current.question_order if current else None},
    )
    result = QuizSessionActionResponse(
        **session_response(quiz_session, len(quiz_session.questions)).model_dump(),
        current_question_id=current.id if current and quiz_session.status != "ENDED" else None,
        current_question_order=current.question_order if current and quiz_session.status != "ENDED" else None,
    )
    if idempotency_record is not None:
        idempotency_record.response_json = result.model_dump_json()
    await session.commit()
    await connection_manager.broadcast(
        session_id,
        "quiz.state.changed",
        {
            "status": quiz_session.status,
            "questionCount": len(quiz_session.questions),
            "currentQuestionId": str(current.id) if current and quiz_session.status != "ENDED" else None,
            "currentQuestionOrder": current.question_order if current and quiz_session.status != "ENDED" else None,
            "question": {
                "prompt": current.prompt_snapshot,
                "codeSnippet": current.code_snippet_snapshot,
                "questionType": current.question_type_snapshot,
                "options": [
                    {"key": option["key"], "text": option["text"]}
                    for option in json.loads(current.answer_key_snapshot or "[]")
                ],
            } if current and quiz_session.status != "ENDED" else None,
        },
    )
    return result


@router.get("/quiz-sessions/{session_id}/questions", response_model=list[QuizSessionQuestionPublic])
async def list_session_questions(session_id: UUID, session: AsyncSession = Depends(get_db_session)) -> list[QuizSessionQuestionPublic]:
    quiz_session = await session.scalar(select(QuizSession).where(QuizSession.id == session_id))
    if quiz_session is None:
        raise AppError("SESSION_NOT_FOUND", "The quiz session or its questions were not found.", 404)
    query = select(QuizQuestion).options(selectinload(QuizQuestion.question)).where(
        QuizQuestion.quiz_session_id == session_id,
        QuizQuestion.opened_at.is_not(None),
        QuizQuestion.closed_at.is_(None),
    )
    items = (await session.scalars(query.order_by(QuizQuestion.question_order))).all()
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
