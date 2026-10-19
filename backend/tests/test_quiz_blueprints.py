import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.session import initialize_local_database


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
