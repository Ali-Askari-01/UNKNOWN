import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.db.models import QuizSession
from app.db.session import SessionFactory, initialize_local_database
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
        await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/open")
        await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/start")
        active_questions = await client.get(f"/api/v1/quiz-sessions/{session_id}/questions")

    assert session.status_code == 201
    assert session.json()["question_count"] == 1
    assert public_questions.status_code == 200
    assert public_questions.json() == []
    assert "is_correct" not in public_questions.text
    assert len(active_questions.json()) == 1
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


@pytest.mark.asyncio
async def test_quiz_session_lifecycle_is_persisted_and_enforces_transitions() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        created = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprints.json()[0]["id"]})
        session_id = created.json()["id"]

        opened = await client.post(
            f"/api/v1/admin/quiz-sessions/{session_id}/actions/open",
            headers={"Idempotency-Key": "session-action-open-test-1"},
        )
        replayed_open = await client.post(
            f"/api/v1/admin/quiz-sessions/{session_id}/actions/open",
            headers={"Idempotency-Key": "session-action-open-test-1"},
        )
        started = await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/start")
        paused = await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/pause")
        invalid_advance = await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/advance")
        resumed = await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/resume")
        advanced = await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/advance")

    async with SessionFactory() as database:
        persisted = await database.get(QuizSession, session_id)

    assert opened.json()["status"] == "OPEN"
    assert replayed_open.status_code == 200
    assert replayed_open.json() == opened.json()
    assert started.json()["status"] == "ACTIVE"
    assert started.json()["current_question_order"] == 1
    assert paused.json()["status"] == "PAUSED"
    assert invalid_advance.status_code == 409
    assert resumed.json()["status"] == "ACTIVE"
    assert advanced.json()["status"] == "ENDED"
    assert advanced.json()["current_question_id"] is None
    assert persisted is not None and persisted.version_id == 6


@pytest.mark.asyncio
async def test_stale_quiz_session_version_cannot_overwrite_a_newer_action() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        created = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprints.json()[0]["id"]})
    assert created.status_code == 201
    session_id = created.json()["id"]

    first = SessionFactory()
    stale = SessionFactory()
    try:
        first_row = await first.get(QuizSession, session_id)
        stale_row = await stale.get(QuizSession, session_id)
        assert first_row is not None and stale_row is not None
        expected_version = first_row.version_id
        assert stale_row.version_id == expected_version

        winner = await first.execute(
            update(QuizSession)
            .where(QuizSession.id == session_id, QuizSession.version_id == expected_version)
            .values(version_id=expected_version + 1)
            .execution_options(synchronize_session=False)
        )
        await first.commit()
        stale_write = await stale.execute(
            update(QuizSession)
            .where(QuizSession.id == session_id, QuizSession.version_id == expected_version)
            .values(version_id=expected_version + 1)
            .execution_options(synchronize_session=False)
        )
        await stale.rollback()
    finally:
        await first.close()
        await stale.close()

    assert winner.rowcount == 1
    assert stale_write.rowcount == 0
