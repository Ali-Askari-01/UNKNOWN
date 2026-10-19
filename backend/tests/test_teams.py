import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import initialize_local_database
from app.main import app


@pytest.fixture(autouse=True)
async def local_database() -> None:
    await initialize_local_database()


@pytest.mark.asyncio
async def test_public_teams_can_resolve_active_edition() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/teams", params={"class_code": "IX"})

    assert response.status_code == 200
    assert response.json()
    assert any(team["name"] in {"Demo Team", "Black Hat Hackers", "404 braincells", "Cyber Deceit", "Unorthodox Hub", "Tech Nawab"} for team in response.json())
