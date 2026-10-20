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
        await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/open")
        await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/start")
        teams = await client.get("/api/v1/teams", params={"edition_id": "00000000-0000-0000-0000-000000000000"})
        # The local seed team is read directly through the database-backed public endpoint in this test.
        from sqlalchemy import select

        from app.db.models import ClassTrack, Team, TeamClass
        from app.db.session import SessionFactory
        async with SessionFactory() as db:
            team = await db.scalar(
                select(Team)
                .join(TeamClass, TeamClass.team_id == Team.id)
                .join(ClassTrack, ClassTrack.id == TeamClass.class_track_id)
                .where(ClassTrack.code == "IX")
            )
        participant = await client.post(
            "/api/v1/auth/team/join",
            json={"quiz_code": quiz.json()["quiz_code"], "team_id": str(team.id)},
            headers={"Idempotency-Key": "team-join-test-1"},
        )
        replayed_participant = await client.post(
            "/api/v1/auth/team/join",
            json={"quiz_code": quiz.json()["quiz_code"], "team_id": str(team.id)},
            headers={"Idempotency-Key": "team-join-test-1"},
        )
        questions = await client.get(f"/api/v1/quiz-sessions/{session_id}/questions")
        answer = await client.post(
            f"/api/v1/quiz-sessions/{session_id}/answers",
            json={"participant_id": participant.json()["id"], "quiz_question_id": questions.json()[0]["id"], "submitted_answer": "B"},
            headers={"Idempotency-Key": "answer-test-1"},
        )
        replayed_answer = await client.post(
            f"/api/v1/quiz-sessions/{session_id}/answers",
            json={"participant_id": participant.json()["id"], "quiz_question_id": questions.json()[0]["id"], "submitted_answer": "B"},
            headers={"Idempotency-Key": "answer-test-1"},
        )
        mismatched_answer_reuse = await client.post(
            f"/api/v1/quiz-sessions/{session_id}/answers",
            json={"participant_id": participant.json()["id"], "quiz_question_id": questions.json()[0]["id"], "submitted_answer": "A"},
            headers={"Idempotency-Key": "answer-test-1"},
        )
        judged_answers = await client.get(f"/api/v1/admin/quiz-sessions/{session_id}/answers")
        leaderboard = await client.get(f"/api/v1/quiz-sessions/{session_id}/leaderboard")

    assert teams.status_code == 200
    assert participant.status_code == 201
    assert replayed_participant.status_code == 201
    assert replayed_participant.json() == participant.json()
    assert answer.json()["is_correct"] is True
    assert answer.json()["awarded_points"] == 10
    assert replayed_answer.status_code == 201
    assert replayed_answer.json() == answer.json()
    assert mismatched_answer_reuse.status_code == 409
    assert mismatched_answer_reuse.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert judged_answers.status_code == 200
    assert judged_answers.json()[0]["submitted_answer"] == "B"
    assert judged_answers.json()[0]["is_correct"] is True
    assert leaderboard.json()[0]["points"] == 10


@pytest.mark.asyncio
async def test_duplicate_final_answer_is_rejected() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        quiz = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprints.json()[0]["id"]})
        session_id = quiz.json()["id"]
        await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/open")
        await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/start")
        from sqlalchemy import select

        from app.db.models import ClassTrack, Team, TeamClass
        from app.db.session import SessionFactory
        async with SessionFactory() as db:
            team = await db.scalar(
                select(Team)
                .join(TeamClass, TeamClass.team_id == Team.id)
                .join(ClassTrack, ClassTrack.id == TeamClass.class_track_id)
                .where(ClassTrack.code == "IX")
            )
        participant = await client.post(
            "/api/v1/auth/team/join",
            json={"quiz_code": quiz.json()["quiz_code"], "team_id": str(team.id)},
        )
        questions = await client.get(f"/api/v1/quiz-sessions/{session_id}/questions")
        await client.post(f"/api/v1/quiz-sessions/{session_id}/questions/{questions.json()[0]['id']}/buzzer")
        payload = {"participant_id": participant.json()["id"], "quiz_question_id": questions.json()[0]["id"], "submitted_answer": "B"}
        first = await client.post(f"/api/v1/quiz-sessions/{session_id}/answers", json=payload)
        second = await client.post(f"/api/v1/quiz-sessions/{session_id}/answers", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_riddle_buzzer_wrong_answer_deducts_and_correct_answer_doubles_points() -> None:
    from uuid import UUID, uuid4

    from sqlalchemy import select

    from app.db.models import ClassTrack, QuizQuestion, Team, TeamClass
    from app.db.session import SessionFactory

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        quiz = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprints.json()[0]["id"]})
        session_id = quiz.json()["id"]
        await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/open")
        await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/start")
        async with SessionFactory() as db:
            question = await db.scalar(select(QuizQuestion).where(QuizQuestion.quiz_session_id == UUID(session_id)))
            question.question_type_snapshot = "RIDDLE"
            question.accepted_answers_snapshot = '["echo"]'
            class_track = await db.scalar(select(ClassTrack).where(ClassTrack.code == "IX"))
            teams = [
                Team(event_edition_id=class_track.event_edition_id, name=f"Riddle Test {uuid4().hex[:8]}")
                for _ in range(2)
            ]
            db.add_all(teams)
            await db.flush()
            db.add_all([TeamClass(team_id=team.id, class_track_id=class_track.id) for team in teams])
            await db.commit()
        joined = [
            await client.post("/api/v1/auth/team/join", json={"quiz_code": quiz.json()["quiz_code"], "team_id": str(team.id)})
            for team in teams
        ]
        question_list = await client.get(f"/api/v1/quiz-sessions/{session_id}/questions")
        question_id = question_list.json()[0]["id"]
        first_auth = {"Authorization": f"Bearer {joined[0].json()['access_token']}"}
        second_auth = {"Authorization": f"Bearer {joined[1].json()['access_token']}"}
        first_buzz = await client.post(f"/api/v1/quiz-sessions/{session_id}/questions/{question_id}/buzzer", headers=first_auth)
        wrong = await client.post(
            f"/api/v1/quiz-sessions/{session_id}/answers",
            headers={**first_auth, "Idempotency-Key": "riddle-answer-one"},
            json={"participant_id": joined[0].json()["id"], "quiz_question_id": question_id, "submitted_answer": "wrong"},
        )
        second_buzz = await client.post(f"/api/v1/quiz-sessions/{session_id}/questions/{question_id}/buzzer", headers=second_auth)
        correct = await client.post(
            f"/api/v1/quiz-sessions/{session_id}/answers",
            headers={**second_auth, "Idempotency-Key": "riddle-answer-two"},
            json={"participant_id": joined[1].json()["id"], "quiz_question_id": question_id, "submitted_answer": "ECHO"},
        )

    assert first_buzz.status_code == 201
    assert wrong.json()["is_correct"] is False
    assert wrong.json()["awarded_points"] == -10
    assert second_buzz.status_code == 201
    assert correct.json()["is_correct"] is True
    assert correct.json()["awarded_points"] == 20


@pytest.mark.asyncio
async def test_public_session_lookup_and_participant_registration() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        quiz = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprints.json()[0]["id"]})
        session = await client.get(f"/api/v1/quiz-sessions/by-code/{quiz.json()['quiz_code']}")
        from sqlalchemy import select

        from app.db.models import ClassTrack, Team, TeamClass
        from app.db.session import SessionFactory
        async with SessionFactory() as db:
            team = await db.scalar(
                select(Team)
                .join(TeamClass, TeamClass.team_id == Team.id)
                .join(ClassTrack, ClassTrack.id == TeamClass.class_track_id)
                .where(ClassTrack.code == "IX")
            )
        participant = await client.post(
            "/api/v1/auth/team/join",
            json={"quiz_code": quiz.json()["quiz_code"], "team_id": str(team.id)},
        )

    assert session.status_code == 200
    assert session.json()["class_code"] == "IX"
    assert participant.status_code == 201


@pytest.mark.asyncio
async def test_participant_mutation_requires_team_authentication() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        quiz = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprints.json()[0]["id"]})
        from sqlalchemy import select

        from app.db.models import ClassTrack, Team, TeamClass
        from app.db.session import SessionFactory
        async with SessionFactory() as db:
            team = await db.scalar(
                select(Team)
                .join(TeamClass, TeamClass.team_id == Team.id)
                .join(ClassTrack, ClassTrack.id == TeamClass.class_track_id)
                .where(ClassTrack.code == "IX")
            )
        response = await client.post(
            f"/api/v1/quiz-sessions/{quiz.json()['id']}/participants",
            json={"team_id": str(team.id)},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_buzzer_is_rejected_for_non_riddle_questions() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        quiz = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprints.json()[0]["id"]})
        session_id = quiz.json()["id"]
        await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/open")
        await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/start")
        from sqlalchemy import select

        from app.db.models import ClassTrack, Team, TeamClass
        from app.db.session import SessionFactory
        async with SessionFactory() as db:
            team = await db.scalar(
                select(Team)
                .join(TeamClass, TeamClass.team_id == Team.id)
                .join(ClassTrack, ClassTrack.id == TeamClass.class_track_id)
                .where(ClassTrack.code == "IX")
            )
        joined = await client.post(
            "/api/v1/auth/team/join",
            json={"quiz_code": quiz.json()["quiz_code"], "team_id": str(team.id)},
        )
        questions = await client.get(f"/api/v1/quiz-sessions/{session_id}/questions")
        question_id = questions.json()[0]["id"]
        first = await client.post(f"/api/v1/quiz-sessions/{session_id}/questions/{question_id}/buzzer")

    assert joined.status_code == 201
    assert first.status_code == 409
    assert first.json()["error"]["code"] == "BUZZER_NOT_OPEN"


@pytest.mark.asyncio
async def test_non_riddle_questions_do_not_create_buzzer_winners() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blueprints = await client.get("/api/v1/quiz-blueprints")
        quiz = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprints.json()[0]["id"]})
        session_id = quiz.json()["id"]
        await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/open")
        await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/start")
        from sqlalchemy import select

        from app.db.models import ClassTrack, Team, TeamClass
        from app.db.session import SessionFactory
        async with SessionFactory() as db:
            team = await db.scalar(select(Team).join(TeamClass).join(ClassTrack).where(ClassTrack.code == "IX"))
        joined = await client.post("/api/v1/auth/team/join", json={"quiz_code": quiz.json()["quiz_code"], "team_id": str(team.id)})
        questions = await client.get(f"/api/v1/quiz-sessions/{session_id}/questions")
        question_id = questions.json()[0]["id"]
        result = await client.post(f"/api/v1/quiz-sessions/{session_id}/questions/{question_id}/buzzer", headers={"Authorization": f"Bearer {joined.json()['access_token']}"})

    assert joined.status_code == 201
    assert result.status_code == 409
