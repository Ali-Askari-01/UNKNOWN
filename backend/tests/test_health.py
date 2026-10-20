from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import health
from app.core import middleware
from app.main import app


async def test_liveness() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "camera=(), geolocation=(), microphone=()"
    assert "strict-transport-security" not in response.headers


@pytest.mark.asyncio
async def test_production_responses_include_hsts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(middleware, "get_settings", lambda: SimpleNamespace(environment="production"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


async def test_root_exposes_request_id() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/", headers={"x-request-id": "phase-1-test"})

    assert response.status_code == 200
    assert response.json()["requestId"] == "phase-1-test"


async def test_error_envelope_exposes_request_id_at_top_level() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/admin/quiz-sessions/00000000-0000-0000-0000-000000000000/actions/start",
            headers={"x-request-id": "error-contract-test"},
        )

    assert response.status_code == 404
    assert response.json()["requestId"] == "error-contract-test"
    assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_production_readiness_requires_the_realtime_relay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "get_settings", lambda: SimpleNamespace(environment="production"))
    monkeypatch.setattr(health, "ping_database", _healthy_database)
    monkeypatch.setattr(health, "get_schema_revision", _current_revision)
    monkeypatch.setattr(
        health.connection_manager,
        "health_snapshot",
        lambda: {"relayRunning": False, "lastEventId": 12, "connectionCount": 0},
    )

    response = await health.readiness()

    assert response.status_code == 503
    assert response.body == b'{"status":"unavailable","realtime":{"relayRunning":false,"lastEventId":12,"connectionCount":0}}'


async def _healthy_database() -> None:
    return None


async def _current_revision() -> str:
    return "0010_auto_quiz_rules"
