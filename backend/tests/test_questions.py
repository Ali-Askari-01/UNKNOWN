import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.session import initialize_local_database


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
