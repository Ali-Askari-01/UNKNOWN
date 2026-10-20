from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.auth import require_admin, require_team
from app.core.audit import add_audit
from app.core.grading import grade_answer
from app.core.idempotency import request_hash, reserve
from app.core.rate_limit import enforce_rate_limit
from app.db.models import AnswerSubmission, BuzzerPress, QuizBlueprint, QuizParticipant, QuizQuestion, QuizSession, ScoreEntry, Team
from app.db.session import get_db_session
from app.realtime.manager import connection_manager
from app.schemas.participation import AdminAnswerResponse, AnswerCreate, AnswerResponse, BuzzerResponse, JudgeAnswerRequest, LeaderboardEntry, ParticipantCreate, ParticipantResponse

router = APIRouter(prefix="/api/v1", tags=["participation"])


@router.post("/quiz-sessions/{session_id}/questions/{question_id}/buzzer", response_model=BuzzerResponse, status_code=201)
async def press_buzzer(
    session_id: UUID,
    question_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    team_identity: dict[str, object] = Depends(require_team),
) -> BuzzerResponse:
    await enforce_rate_limit(request, "buzzer", limit=5, window_seconds=5, identity=str(team_identity.get("sub")))
    if team_identity.get("session_id") != str(session_id):
        raise AppError("TEAM_SCOPE_MISMATCH", "The team token does not belong to this quiz session.", 403)
    try:
        team_id = UUID(str(team_identity["sub"]))
        participant_id = UUID(str(team_identity["participant_id"]))
    except (KeyError, TypeError, ValueError) as error:
        raise AppError("INVALID_TEAM_TOKEN", "The team authentication token is invalid.", 401) from error
    participant = await session.scalar(
        select(QuizParticipant).where(
            QuizParticipant.id == participant_id,
            QuizParticipant.quiz_session_id == session_id,
            QuizParticipant.team_id == team_id,
            QuizParticipant.left_at.is_(None),
        )
    )
    quiz_session = await session.scalar(select(QuizSession).where(QuizSession.id == session_id))
    question = await session.scalar(select(QuizQuestion).where(QuizQuestion.id == question_id, QuizQuestion.quiz_session_id == session_id))
    team = await session.scalar(select(Team).where(Team.id == team_id))
    blueprint = await session.scalar(select(QuizBlueprint).where(QuizBlueprint.id == quiz_session.blueprint_id)) if quiz_session else None
    if participant is None or team is None or quiz_session is None or question is None or blueprint is None:
        raise AppError("INVALID_BUZZER_CONTEXT", "The team, session, and question must belong together.", 400)
    if quiz_session.status != "ACTIVE" or question.opened_at is None or question.closed_at is not None or not blueprint.buzzer_enabled or question.question_type_snapshot != "RIDDLE":
        raise AppError("BUZZER_NOT_OPEN", "The buzzer is not accepting presses for this question.", 409)
    existing_winner = await session.scalar(select(BuzzerPress).where(BuzzerPress.quiz_question_id == question_id, BuzzerPress.is_winner))
    if existing_winner is not None:
        winner_pressed_at = existing_winner.pressed_at
        if winner_pressed_at.tzinfo is None:
            winner_pressed_at = winner_pressed_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) <= winner_pressed_at + timedelta(seconds=blueprint.seconds_per_question):
            raise AppError("BUZZER_ALREADY_WON", "Another team has already won this question.", 409)
        existing_winner.is_winner = False
        await session.flush()
    prior_answer = await session.scalar(select(AnswerSubmission.id).where(AnswerSubmission.quiz_question_id == question_id, AnswerSubmission.participant_id == participant.id, AnswerSubmission.is_final))
    if prior_answer is not None:
        raise AppError("ANSWER_ALREADY_SUBMITTED", "Your team has already answered this riddle.", 409)

    pressed_at = datetime.now(timezone.utc)
    press = BuzzerPress(quiz_question_id=question_id, participant_id=participant.id, pressed_at=pressed_at, is_winner=True)
    session.add(press)
    try:
        await session.flush()
        add_audit(session, action_code="BUZZER_WON", entity_name="buzzer_press", entity_id=press.id, details={"session_id": str(session_id), "team_id": str(participant.team_id)})
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if "buzzer" in str(error).lower() or "ux_buzzer_one_winner" in str(error).lower():
            raise AppError("BUZZER_ALREADY_WON", "Another team has already won this question.", 409) from error
        raise
    deadline = pressed_at + timedelta(seconds=blueprint.seconds_per_question)
    await connection_manager.broadcast(session_id, "quiz.buzzer.accepted", {"questionId": str(question_id), "participantId": str(participant.id), "teamName": team.name, "answerDeadline": deadline.isoformat()})
    return BuzzerResponse(id=press.id, quiz_question_id=question_id, participant_id=participant.id, team_name=team.name, is_winner=True, answer_deadline=deadline.isoformat())


@router.post("/quiz-sessions/{session_id}/participants", response_model=ParticipantResponse, status_code=201)
async def register_participant(session_id: UUID, payload: ParticipantCreate, session: AsyncSession = Depends(get_db_session), team_identity: dict[str, object] = Depends(require_team)) -> ParticipantResponse:
    if team_identity.get("session_id") != str(session_id) or team_identity.get("sub") != str(payload.team_id):
        raise AppError("TEAM_SCOPE_MISMATCH", "The team token does not belong to this quiz session.", 403)
    quiz_session = await session.scalar(select(QuizSession).where(QuizSession.id == session_id))
    team = await session.scalar(select(Team).where(Team.id == payload.team_id))
    if quiz_session is None or team is None or team.event_edition_id is None or quiz_session.status not in {"WAITING", "ACTIVE"}:
        raise AppError("INVALID_PARTICIPANT", "The quiz session or team was not found.", 404)
    existing = await session.scalar(select(QuizParticipant).where(QuizParticipant.quiz_session_id == session_id, QuizParticipant.team_id == payload.team_id, QuizParticipant.left_at.is_(None)))
    if existing is not None:
        return ParticipantResponse(id=existing.id, quiz_session_id=existing.quiz_session_id, team_id=existing.team_id)
    participant = QuizParticipant(quiz_session_id=session_id, team_id=payload.team_id)
    session.add(participant)
    await session.flush()
    add_audit(session, action_code="PARTICIPANT_REGISTERED", entity_name="quiz_participant", entity_id=participant.id, details={"session_id": str(session_id), "team_id": str(payload.team_id)})
    await session.commit()
    return ParticipantResponse(id=participant.id, quiz_session_id=participant.quiz_session_id, team_id=participant.team_id)


@router.post("/quiz-sessions/{session_id}/answers", response_model=AnswerResponse, status_code=201)
async def submit_answer(session_id: UUID, payload: AnswerCreate, request: Request, session: AsyncSession = Depends(get_db_session), team_identity: dict[str, object] = Depends(require_team)) -> AnswerResponse:
    await enforce_rate_limit(request, "answer", limit=5, window_seconds=10, identity=str(team_identity.get("sub")))
    if team_identity.get("session_id") != str(session_id) or team_identity.get("participant_id") != str(payload.participant_id):
        raise AppError("TEAM_SCOPE_MISMATCH", "The team token does not belong to this participant.", 403)
    try:
        team_id = UUID(str(team_identity["sub"]))
        participant_id = UUID(str(team_identity["participant_id"]))
    except (KeyError, TypeError, ValueError) as error:
        raise AppError("INVALID_TEAM_TOKEN", "The team authentication token is invalid.", 401) from error
    participant = await session.scalar(select(QuizParticipant).where(QuizParticipant.id == participant_id, QuizParticipant.quiz_session_id == session_id, QuizParticipant.team_id == team_id, QuizParticipant.left_at.is_(None)))
    quiz_question = await session.scalar(select(QuizQuestion).where(QuizQuestion.id == payload.quiz_question_id, QuizQuestion.quiz_session_id == session_id))
    if participant is None or quiz_question is None:
        raise AppError("INVALID_ANSWER_CONTEXT", "The participant and question must belong to this quiz session.", 400)
    is_riddle = quiz_question.question_type_snapshot == "RIDDLE"
    winning_press = await session.scalar(select(BuzzerPress).where(BuzzerPress.quiz_question_id == quiz_question.id, BuzzerPress.participant_id == participant.id, BuzzerPress.is_winner)) if is_riddle else None
    if is_riddle and winning_press is None:
        raise AppError("BUZZER_REQUIRED", "Only the team that won the buzzer may answer this question.", 409)
    quiz_session = await session.scalar(select(QuizSession).where(QuizSession.id == session_id))
    blueprint = await session.scalar(select(QuizBlueprint).where(QuizBlueprint.id == quiz_session.blueprint_id)) if quiz_session else None
    if quiz_session is None or blueprint is None or quiz_session.status != "ACTIVE" or quiz_question.opened_at is None or quiz_question.closed_at is not None:
        raise AppError("ANSWER_NOT_OPEN", "This question is not accepting answers.", 409)
    pressed_at = winning_press.pressed_at if winning_press is not None else quiz_question.opened_at
    if pressed_at.tzinfo is None:
        pressed_at = pressed_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > pressed_at + timedelta(seconds=blueprint.seconds_per_question):
        raise AppError("ANSWER_WINDOW_EXPIRED", "The answer window has expired.", 409)
    idempotency_record = await reserve(
        session,
        scope_key=f"answer:{session_id}:{participant.id}:{quiz_question.id}",
        key=request.headers.get("Idempotency-Key"),
        payload_hash=request_hash(payload.model_dump(mode="json")),
    )
    if idempotency_record is not None and idempotency_record.response_json:
        return AnswerResponse.model_validate_json(idempotency_record.response_json)

    existing = await session.scalar(select(AnswerSubmission).where(AnswerSubmission.quiz_question_id == quiz_question.id, AnswerSubmission.participant_id == participant.id, AnswerSubmission.is_final))
    if existing is not None:
        raise AppError("ANSWER_ALREADY_SUBMITTED", "A final answer has already been submitted for this question.", 409)

    is_correct = grade_answer(quiz_question.question_type_snapshot, payload.submitted_answer, quiz_question.answer_key_snapshot, quiz_question.accepted_answers_snapshot)
    if is_riddle and is_correct is None:
        raise AppError("RIDDLE_ANSWER_KEY_MISSING", "This riddle has no accepted answer configured and cannot be auto-scored.", 409)
    awarded_points = (quiz_question.points_snapshot * 2 if is_correct else -quiz_question.points_snapshot) if is_riddle else (quiz_question.points_snapshot if is_correct else 0)
    answer = AnswerSubmission(
        quiz_question_id=quiz_question.id,
        participant_id=participant.id,
        buzzer_press_id=winning_press.id if winning_press is not None else None,
        submitted_answer=payload.submitted_answer.strip(),
        is_final=True,
        is_correct=is_correct,
        awarded_points=awarded_points,
        judged_at=datetime.now(timezone.utc) if is_correct is not None else None,
    )
    session.add(answer)
    try:
        await session.flush()
        response = AnswerResponse(id=answer.id, quiz_question_id=answer.quiz_question_id, is_correct=is_correct, awarded_points=awarded_points)
        if is_correct is not None:
            round_id = await session.scalar(select(QuizBlueprint.round_id).where(QuizBlueprint.id == blueprint.id))
            session.add(ScoreEntry(team_id=participant.team_id, round_id=round_id, quiz_session_id=session_id, answer_submission_id=answer.id, points_delta=awarded_points, reason="ANSWER"))
            if is_riddle and is_correct:
                quiz_question.closed_at = datetime.now(timezone.utc)
            elif is_riddle and winning_press is not None:
                winning_press.is_winner = False
        add_audit(session, action_code="ANSWER_SUBMITTED", entity_name="answer_submission", entity_id=answer.id, details={"correct": is_correct, "points": awarded_points})
        if idempotency_record is not None:
            idempotency_record.response_json = response.model_dump_json()
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if "answer" in str(error).lower() or "ux_answer_one_final" in str(error).lower():
            raise AppError("ANSWER_ALREADY_SUBMITTED", "A final answer has already been submitted for this question.", 409) from error
        raise
    await connection_manager.broadcast(session_id, "quiz.answer.submitted", {"questionId": str(answer.quiz_question_id), "answerId": str(answer.id), "participantId": str(participant.id), "correct": is_correct, "points": awarded_points, "buzzerOpen": is_riddle and is_correct is False, "questionClosed": is_riddle and is_correct is True})
    if is_correct is not None:
        await connection_manager.broadcast(session_id, "quiz.answer.judged", {"questionId": str(answer.quiz_question_id), "answerId": str(answer.id), "teamId": str(participant.team_id), "correct": is_correct, "points": awarded_points})
    return response


@router.post("/admin/quiz-sessions/{session_id}/answers/{answer_id}/judge", response_model=AnswerResponse)
async def judge_answer(
    session_id: UUID,
    answer_id: UUID,
    payload: JudgeAnswerRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin_identity: dict[str, object] = Depends(require_admin),
) -> AnswerResponse:
    idempotency_record = await reserve(
        session,
        scope_key=f"judge:{session_id}:{answer_id}:{admin_identity.get('sub')}",
        key=request.headers.get("Idempotency-Key"),
        payload_hash=request_hash(payload.model_dump(mode="json")),
    )
    if idempotency_record is not None and idempotency_record.response_json:
        return AnswerResponse.model_validate_json(idempotency_record.response_json)
    answer = await session.scalar(select(AnswerSubmission).where(AnswerSubmission.id == answer_id))
    quiz_question = await session.scalar(select(QuizQuestion).where(QuizQuestion.id == answer.quiz_question_id, QuizQuestion.quiz_session_id == session_id)) if answer else None
    participant = await session.scalar(select(QuizParticipant).where(QuizParticipant.id == answer.participant_id, QuizParticipant.quiz_session_id == session_id)) if answer else None
    blueprint_id = await session.scalar(select(QuizSession.blueprint_id).where(QuizSession.id == session_id))
    blueprint = await session.scalar(select(QuizBlueprint).where(QuizBlueprint.id == blueprint_id)) if blueprint_id else None
    if answer is None or quiz_question is None or participant is None or blueprint is None:
        raise AppError("ANSWER_NOT_FOUND", "The answer does not belong to this quiz session.", 404)
    if answer.is_correct is not None:
        raise AppError("ANSWER_ALREADY_JUDGED", "This answer has already been judged.", 409)
    points = payload.awarded_points if payload.awarded_points is not None else (quiz_question.points_snapshot if payload.is_correct else 0)
    answer.is_correct = payload.is_correct
    answer.awarded_points = points
    answer.judged_at = datetime.now(timezone.utc)
    round_id = await session.scalar(select(QuizBlueprint.round_id).where(QuizBlueprint.id == blueprint.id))
    session.add(ScoreEntry(team_id=participant.team_id, round_id=round_id, quiz_session_id=session_id, answer_submission_id=answer.id, points_delta=points, reason="ANSWER"))
    add_audit(session, action_code="ANSWER_JUDGED", entity_name="answer_submission", entity_id=answer.id, details={"correct": payload.is_correct, "points": points})
    response = AnswerResponse(id=answer.id, quiz_question_id=answer.quiz_question_id, is_correct=payload.is_correct, awarded_points=points)
    if idempotency_record is not None:
        idempotency_record.response_json = response.model_dump_json()
    await session.commit()
    await connection_manager.broadcast(
        session_id,
        "quiz.answer.judged",
        {
            "questionId": str(answer.quiz_question_id),
            "answerId": str(answer.id),
            "teamId": str(participant.team_id),
            "correct": payload.is_correct,
            "points": points,
        },
    )
    return response


@router.get("/admin/quiz-sessions/{session_id}/answers", response_model=list[AdminAnswerResponse])
async def list_session_answers(
    session_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: dict[str, object] = Depends(require_admin),
) -> list[AdminAnswerResponse]:
    query = (
        select(AnswerSubmission, QuizQuestion.question_order, Team.name)
        .join(QuizQuestion, QuizQuestion.id == AnswerSubmission.quiz_question_id)
        .join(QuizParticipant, QuizParticipant.id == AnswerSubmission.participant_id)
        .join(Team, Team.id == QuizParticipant.team_id)
        .where(QuizQuestion.quiz_session_id == session_id)
        .order_by(AnswerSubmission.submitted_at, QuizQuestion.question_order)
    )
    rows = (await session.execute(query)).all()
    return [
        AdminAnswerResponse(
            id=answer.id,
            quiz_question_id=answer.quiz_question_id,
            question_order=question_order,
            team_name=team_name,
            submitted_answer=answer.submitted_answer,
            is_correct=answer.is_correct,
            awarded_points=answer.awarded_points,
            submitted_at=answer.submitted_at.isoformat(),
        )
        for answer, question_order, team_name in rows
    ]


@router.get("/quiz-sessions/{session_id}/leaderboard", response_model=list[LeaderboardEntry])
async def session_leaderboard(session_id: UUID, session: AsyncSession = Depends(get_db_session)) -> list[LeaderboardEntry]:
    query = (
        select(Team.id, Team.name, func.coalesce(func.sum(ScoreEntry.points_delta), 0).label("points"))
        .join(ScoreEntry, ScoreEntry.team_id == Team.id)
        .where(ScoreEntry.quiz_session_id == session_id)
        .group_by(Team.id, Team.name)
        .order_by(func.sum(ScoreEntry.points_delta).desc(), Team.name)
    )
    return [LeaderboardEntry(team_id=team_id, team_name=name, points=points) for team_id, name, points in (await session.execute(query)).all()]
