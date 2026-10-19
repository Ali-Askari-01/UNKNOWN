import json
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.audit import add_audit
from app.db.models import AnswerSubmission, QuizParticipant, QuizQuestion, QuizSession, ScoreEntry, Team
from app.db.session import get_db_session
from app.schemas.participation import AnswerCreate, AnswerResponse, LeaderboardEntry, ParticipantCreate, ParticipantResponse

router = APIRouter(prefix="/api/v1", tags=["participation"])


@router.post("/quiz-sessions/{session_id}/participants", response_model=ParticipantResponse, status_code=201)
async def register_participant(session_id: UUID, payload: ParticipantCreate, session: AsyncSession = Depends(get_db_session)) -> ParticipantResponse:
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
async def submit_answer(session_id: UUID, payload: AnswerCreate, session: AsyncSession = Depends(get_db_session)) -> AnswerResponse:
    participant = await session.scalar(select(QuizParticipant).where(QuizParticipant.id == payload.participant_id, QuizParticipant.quiz_session_id == session_id, QuizParticipant.left_at.is_(None)))
    quiz_question = await session.scalar(select(QuizQuestion).where(QuizQuestion.id == payload.quiz_question_id, QuizQuestion.quiz_session_id == session_id))
    if participant is None or quiz_question is None:
        raise AppError("INVALID_ANSWER_CONTEXT", "The participant and question must belong to this quiz session.", 400)
    existing = await session.scalar(select(AnswerSubmission).where(AnswerSubmission.quiz_question_id == quiz_question.id, AnswerSubmission.participant_id == participant.id, AnswerSubmission.is_final == True))
    if existing is not None:
        raise AppError("ANSWER_ALREADY_SUBMITTED", "A final answer has already been submitted for this question.", 409)

    answer_options = json.loads(quiz_question.answer_key_snapshot or "[]")
    correct_keys = {item["key"].strip().upper() for item in answer_options if item.get("is_correct")}
    is_correct = payload.submitted_answer.strip().upper() in correct_keys
    points = quiz_question.points_snapshot if is_correct else 0
    answer = AnswerSubmission(
        quiz_question_id=quiz_question.id,
        participant_id=participant.id,
        submitted_answer=payload.submitted_answer.strip(),
        is_final=True,
        is_correct=is_correct,
        awarded_points=points,
    )
    session.add(answer)
    await session.flush()
    blueprint_round = await session.scalar(select(QuizSession.blueprint_id).where(QuizSession.id == session_id))
    round_id = await session.scalar(select(ScoreEntry.round_id).where(ScoreEntry.quiz_session_id == session_id).limit(1))
    if round_id is None:
        from app.db.models import QuizBlueprint
        round_id = await session.scalar(select(QuizBlueprint.round_id).where(QuizBlueprint.id == blueprint_round))
    session.add(ScoreEntry(team_id=participant.team_id, round_id=round_id, quiz_session_id=session_id, answer_submission_id=answer.id, points_delta=points, reason="ANSWER"))
    add_audit(session, action_code="ANSWER_SUBMITTED", entity_name="answer_submission", entity_id=answer.id, details={"correct": is_correct, "points": points})
    await session.commit()
    return AnswerResponse(id=answer.id, quiz_question_id=answer.quiz_question_id, is_correct=is_correct, awarded_points=points)


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
