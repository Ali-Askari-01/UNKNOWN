import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import initialize_local_database
from app.main import app


@pytest.fixture(autouse=True)
async def local_database() -> None:
    await initialize_local_database()


@pytest.mark.asyncio
async def test_seeded_blueprint_has_matching_distribution() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/quiz-blueprints")

    assert response.status_code == 200
    blueprint = response.json()[0]
    assert sum(item["quantity"] for item in blueprint["distributions"]) == blueprint["question_count"]


@pytest.mark.asyncio
async def test_invalid_distribution_total_is_rejected() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/admin/quiz-blueprints",
            json={
                "round_id": "00000000-0000-0000-0000-000000000000",
                "class_track_id": "00000000-0000-0000-0000-000000000000",
                "name": "Invalid",
                "question_count": 10,
                "distributions": [{"question_type": "MCQ", "difficulty": "EASY", "quantity": 9}],
            },
        )

    assert response.status_code == 422
    assert "Distribution quantities" in response.json()["error"]["fields"][0]["message"]


@pytest.mark.asyncio
async def test_standard_blueprint_has_required_distribution_and_rejects_incomplete_bank() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        classes = await client.get("/api/v1/classes")
        class_track_id = classes.json()[0]["id"]
        blueprint_response = await client.post(
            "/api/v1/admin/quiz-blueprints/standard",
            params={"class_track_id": class_track_id},
        )
        assert blueprint_response.status_code == 200
        blueprint = blueprint_response.json()
        distribution = {item["question_type"]: item["quantity"] for item in blueprint["distributions"]}
        repeated_blueprint_response = await client.post(
            "/api/v1/admin/quiz-blueprints/standard",
            params={"class_track_id": class_track_id},
        )
        session_response = await client.post("/api/v1/admin/quiz-sessions", json={"blueprint_id": blueprint["id"]})

    assert blueprint["question_count"] == 30
    assert distribution == {"CONCEPTUAL": 10, "RIDDLE": 5, "THEORY": 5, "DEBUGGING": 10}
    assert repeated_blueprint_response.status_code == 200
    assert repeated_blueprint_response.json()["id"] == blueprint["id"]
    assert session_response.status_code == 409
    assert session_response.json()["error"]["code"] == "INSUFFICIENT_QUESTION_BANK"
