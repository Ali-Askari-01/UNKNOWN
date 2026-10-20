from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import initialize_local_database
from app.main import app


@pytest.fixture(autouse=True)
async def local_database() -> None:
    await initialize_local_database()


@pytest.mark.asyncio
async def test_public_questions_never_expose_answer_keys() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/questions", params={"class_code": "IX"})

    assert response.status_code == 200
    assert response.json()
    assert "is_correct" not in response.text
    assert "explanation" not in response.text


@pytest.mark.asyncio
async def test_admin_questions_include_answer_keys() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/admin/questions")

    assert response.status_code == 200
    assert response.json()[0]["options"]
    assert any("is_correct" in option for option in response.json()[0]["options"])


@pytest.mark.asyncio
async def test_admin_question_creation_rejects_partially_invalid_class_selection() -> None:
    transport = ASGITransport(app=app, client=(f"question-create-{uuid4()}", 43100))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        classes = await client.get("/api/v1/classes")
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "change-me-in-development"},
        )
        response = await client.post(
            "/api/v1/admin/questions",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
            json={
                "question_type": "THEORY",
                "difficulty": "EASY",
                "prompt": "This must not be persisted.",
                "accepted_answers": ["sample answer"],
                "class_track_ids": [classes.json()[0]["id"], str(uuid4())],
                "options": [],
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CLASS_TRACK"
