import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import initialize_local_database
from app.main import app


@pytest.fixture(autouse=True)
async def local_database() -> None:
    await initialize_local_database()


@pytest.mark.asyncio
async def test_register_answer_and_build_leaderboard() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        quiz = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprints.json()[0]["id"]})
        session_id = quiz.json()["id"]
        teams = await client.get("/api/v1/teams", params={"edition_id": "00000000-0000-0000-0000-000000000000"})
        # The local seed team is read directly through the database-backed public endpoint in this test.
        from sqlalchemy import select
        from app.db.models import Team
        from app.db.session import SessionFactory
        async with SessionFactory() as db:
            team = await db.scalar(select(Team))
        participant = await client.post(f"/api/v1/quiz-sessions/{session_id}/participants", json={"team_id": str(team.id)})
        questions = await client.get(f"/api/v1/quiz-sessions/{session_id}/questions")
        answer = await client.post(
            f"/api/v1/quiz-sessions/{session_id}/answers",
            json={"participant_id": participant.json()["id"], "quiz_question_id": questions.json()[0]["id"], "submitted_answer": "B"},
        )
        leaderboard = await client.get(f"/api/v1/quiz-sessions/{session_id}/leaderboard")

    assert teams.status_code == 200
    assert participant.status_code == 201
    assert answer.json()["is_correct"] is True
    assert answer.json()["awarded_points"] == 10
    assert leaderboard.json()[0]["points"] == 10


@pytest.mark.asyncio
async def test_duplicate_final_answer_is_rejected() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        quiz = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprints.json()[0]["id"]})
        session_id = quiz.json()["id"]
        from sqlalchemy import select
        from app.db.models import Team
        from app.db.session import SessionFactory
        async with SessionFactory() as db:
            team = await db.scalar(select(Team))
        participant = await client.post(f"/api/v1/quiz-sessions/{session_id}/participants", json={"team_id": str(team.id)})
        questions = await client.get(f"/api/v1/quiz-sessions/{session_id}/questions")
        payload = {"participant_id": participant.json()["id"], "quiz_question_id": questions.json()[0]["id"], "submitted_answer": "B"}
        first = await client.post(f"/api/v1/quiz-sessions/{session_id}/answers", json=payload)
        second = await client.post(f"/api/v1/quiz-sessions/{session_id}/answers", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_public_session_lookup_and_participant_registration() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        quiz = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprints.json()[0]["id"]})
        session = await client.get(f"/api/v1/quiz-sessions/by-code/{quiz.json()['quiz_code']}")
        from sqlalchemy import select
        from app.db.models import Team
        from app.db.session import SessionFactory
        async with SessionFactory() as db:
            team = await db.scalar(select(Team))
        participant = await client.post(
            f"/api/v1/quiz-sessions/{session.json()['id']}/participants",
            json={"team_id": str(team.id)},
        )

    assert session.status_code == 200
    assert session.json()["class_code"] == "IX"
    assert participant.status_code == 201
