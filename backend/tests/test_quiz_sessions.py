import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import initialize_local_database
from app.main import app


@pytest.fixture(autouse=True)
async def local_database() -> None:
    await initialize_local_database()


@pytest.mark.asyncio
async def test_quiz_session_snapshots_questions_and_hides_answer_key_publicly() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        session = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprints.json()[0]["id"]})
        session_id = session.json()["id"]
        public_questions = await client.get(f"/api/v1/quiz-sessions/{session_id}/questions")
        admin_questions = await client.get(f"/api/v1/admin/quiz-sessions/{session_id}/questions")

    assert session.status_code == 201
    assert session.json()["question_count"] == 1
    assert public_questions.status_code == 200
    assert "is_correct" not in public_questions.text
    assert admin_questions.status_code == 200
    assert "is_correct" in admin_questions.text


@pytest.mark.asyncio
async def test_session_generation_rejects_unavailable_distribution() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        blueprint = blueprints.json()[0]
        classes = await client.get("/api/v1/classes")
        class_x = next(item for item in classes.json() if item["code"] == "X")
        admin_blueprints = await client.get("/api/v1/admin/quiz-blueprints")
        class_x_blueprint = next((item for item in admin_blueprints.json() if item["class_track_id"] == class_x["id"]), None)
        if class_x_blueprint is None:
            new_blueprint = await client.post(
                "/api/v1/admin/quiz-blueprints",
                json={
                    "round_id": blueprint["round_id"],
                    "class_track_id": class_x["id"],
                    "name": "Class X unavailable fixture",
                    "question_count": 1,
                    "distributions": [{"question_type": "MCQ", "difficulty": "EASY", "quantity": 1}],
                },
            )
            class_x_blueprint = new_blueprint.json()
        session = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": class_x_blueprint["id"]})

    assert session.status_code == 409
    assert session.json()["error"]["code"] == "INSUFFICIENT_QUESTION_BANK"
