import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_admin_login_issues_signed_token() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "change-me-in-development"})

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"].count(".") == 1


@pytest.mark.asyncio
async def test_invalid_admin_login_is_rejected() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_reports_valid_identity_and_rejects_invalid_identity() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "change-me-in-development"},
        )
        token = login.json()["access_token"]
        authenticated = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        unauthenticated = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token"},
        )

    assert authenticated.status_code == 200
    assert authenticated.json()["authenticated"] is True
    assert authenticated.json()["role"] == "ADMIN"
    assert authenticated.json()["subject"] == "admin"
    assert unauthenticated.status_code == 200
    assert unauthenticated.json() == {"authenticated": False, "role": None, "subject": None}
