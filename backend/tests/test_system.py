import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_system_status_reports_migration_state() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "fastapi"
    assert payload["apiVersion"] == "v1"
    assert payload["realtime"] == "socketio-compatibility-bridge"
