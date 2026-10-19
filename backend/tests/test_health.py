from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_liveness() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


async def test_root_exposes_request_id() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/", headers={"x-request-id": "phase-1-test"})

    assert response.status_code == 200
    assert response.json()["requestId"] == "phase-1-test"
