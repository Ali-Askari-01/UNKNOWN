import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select

from app.core.auth import verify_admin_token, verify_team_token
from app.db.models import BuzzerPress, QuizBlueprint, QuizParticipant, QuizQuestion, QuizSession, ScoreEntry, Team
from app.db.session import SessionFactory
from app.realtime.manager import connection_manager

router = APIRouter(tags=["realtime"])


@router.websocket("/api/v1/ws/quiz/{session_id}")
async def quiz_realtime(websocket: WebSocket, session_id: UUID) -> None:
    token = websocket.headers.get("authorization", "").removeprefix("Bearer ").strip()
    auth_subprotocol = next(
        (
            value.strip()
            for value in websocket.headers.get("sec-websocket-protocol", "").split(",")
            if value.strip().startswith("auth.")
        ),
        None,
    )
    token = token or websocket.cookies.get("unknown_admin_session") or websocket.cookies.get("unknown_team_session")
    token = token or (auth_subprotocol[5:] if auth_subprotocol else None)
    admin = verify_admin_token(token)
    team = verify_team_token(token)
    if admin is None and (team is None or team.get("session_id") != str(session_id)):
        await websocket.close(code=4401)
        return
    try:
        async with SessionFactory() as session:
            quiz_session, blueprint = (
                await session.execute(
                    select(QuizSession, QuizBlueprint)
                    .join(QuizBlueprint, QuizBlueprint.id == QuizSession.blueprint_id)
                    .where(QuizSession.id == session_id)
                )
            ).first() or (None, None)
            questions = (await session.scalars(select(QuizQuestion).where(QuizQuestion.quiz_session_id == session_id).order_by(QuizQuestion.question_order))).all()
            winning_press = None
            winner_team_name = None
            if questions:
                current_question = next((item for item in questions if item.opened_at is not None and item.closed_at is None), None)
                if current_question is not None:
                    winning_press = await session.scalar(select(BuzzerPress).where(BuzzerPress.quiz_question_id == current_question.id, BuzzerPress.is_winner))
                    if winning_press is not None:
                        winner_team_name = await session.scalar(
                            select(Team.name)
                            .join(QuizParticipant, QuizParticipant.team_id == Team.id)
                            .where(QuizParticipant.id == winning_press.participant_id)
                        )
            score_rows = (
                await session.execute(
                    select(Team.name, func.coalesce(func.sum(ScoreEntry.points_delta), 0))
                    .join(QuizParticipant, QuizParticipant.team_id == Team.id)
                    .outerjoin(
                        ScoreEntry,
                        (ScoreEntry.team_id == Team.id) & (ScoreEntry.quiz_session_id == session_id),
                    )
                    .where(QuizParticipant.quiz_session_id == session_id, QuizParticipant.left_at.is_(None))
                    .group_by(Team.id, Team.name)
                    .order_by(func.coalesce(func.sum(ScoreEntry.points_delta), 0).desc(), Team.name)
                )
            ).all()
        if quiz_session is None:
            await websocket.close(code=4404)
            return
        await connection_manager.connect(session_id, websocket, subprotocol=auth_subprotocol)
        current = next((item for item in questions if item.opened_at is not None and item.closed_at is None), None)
        snapshot_sequence = await connection_manager.reserve_snapshot_sequence(session_id)
        answer_deadline = None
        buzzer_state = "off"
        if quiz_session.status == "ACTIVE" and current is not None and blueprint is not None:
            if current.question_type_snapshot != "RIDDLE":
                opened_at = current.opened_at
                if opened_at is not None:
                    if opened_at.tzinfo is None:
                        opened_at = opened_at.replace(tzinfo=timezone.utc)
                    answer_deadline = (opened_at + timedelta(seconds=blueprint.seconds_per_question)).isoformat()
            elif winning_press is None:
                buzzer_state = "open" if blueprint.buzzer_enabled else "off"
            else:
                pressed_at = winning_press.pressed_at
                if pressed_at.tzinfo is None:
                    pressed_at = pressed_at.replace(tzinfo=timezone.utc)
                answer_deadline = (pressed_at + timedelta(seconds=blueprint.seconds_per_question)).isoformat()
                buzzer_state = "locked" if datetime.now(timezone.utc) < pressed_at + timedelta(seconds=blueprint.seconds_per_question) else "expired"
        await websocket.send_json(
            {
                "eventId": f"snapshot-{session_id}-{snapshot_sequence}",
                "type": "quiz.state.snapshot",
                "sessionId": str(session_id),
                "sequence": snapshot_sequence,
                "serverTime": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "status": quiz_session.status,
                    "questionCount": len(questions),
                    "currentQuestionId": str(current.id) if current else None,
                    "currentQuestionOrder": current.question_order if current else None,
                    "buzzerState": buzzer_state,
                    "buzzerWinner": winner_team_name,
                    "answerDeadline": answer_deadline,
                    "scores": [{"groupName": name, "score": int(points)} for name, points in score_rows],
                    "question": {
                        "prompt": current.prompt_snapshot,
                        "codeSnippet": current.code_snippet_snapshot,
                        "questionType": current.question_type_snapshot,
                        "options": [
                            {"key": option["key"], "text": option["text"]}
                            for option in json.loads(current.answer_key_snapshot or "[]")
                        ],
                    } if current else None,
                },
            }
        )
        while True:
            message = await websocket.receive_json()
            if message.get("type") in {"ping", "quiz.ping"}:
                await websocket.send_json({"type": "quiz.ping.ack", "sessionId": str(session_id)})
            elif message.get("type") == "quiz.snapshot.request":
                await websocket.send_json({"type": "quiz.snapshot.request.ack", "sessionId": str(session_id)})
            else:
                await websocket.send_json({"type": "error", "code": "UNSUPPORTED_EVENT"})
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(session_id, websocket)
