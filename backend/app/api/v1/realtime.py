from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.db.models import QuizQuestion, QuizSession
from app.db.session import SessionFactory

router = APIRouter(tags=["realtime"])


@router.websocket("/api/v1/ws/quiz/{session_id}")
async def quiz_realtime(websocket: WebSocket, session_id: UUID) -> None:
    await websocket.accept()
    try:
        async with SessionFactory() as session:
            quiz_session = await session.scalar(select(QuizSession).where(QuizSession.id == session_id))
            questions = (await session.scalars(select(QuizQuestion).where(QuizQuestion.quiz_session_id == session_id).order_by(QuizQuestion.question_order))).all()
        if quiz_session is None:
            await websocket.send_json({"type": "error", "code": "SESSION_NOT_FOUND"})
            await websocket.close(code=4404)
            return
        await websocket.send_json(
            {
                "eventId": f"snapshot-{session_id}",
                "type": "quiz.state.snapshot",
                "sessionId": str(session_id),
                "sequence": 1,
                "serverTime": datetime.now(timezone.utc).isoformat(),
                "payload": {"status": quiz_session.status, "questionCount": len(questions)},
            }
        )
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong", "sessionId": str(session_id), "sequence": 2})
            else:
                await websocket.send_json({"type": "error", "code": "UNSUPPORTED_EVENT"})
    except WebSocketDisconnect:
        return
