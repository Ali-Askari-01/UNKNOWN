import asyncio
import base64
import json
from uuid import uuid4

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import _sign, verify_admin_token, verify_team_token
from app.core.config import Settings, get_settings
from app.main import app
from scripts.generate_password_hash import hash_password


def isolated_transport(label: str) -> ASGITransport:
    return ASGITransport(app=app, client=(f"{label}-{uuid4()}", 43100))


@pytest.mark.asyncio
async def test_admin_login_issues_signed_token() -> None:
    transport = isolated_transport("login")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "change-me-in-development"})

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"].count(".") == 1
    assert "unknown_admin_session=" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_invalid_admin_login_is_rejected() -> None:
    transport = isolated_transport("invalid-login")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            headers={"x-request-id": "auth-error-contract-test"},
            json={"username": "admin", "password": "wrong"},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert response.json()["requestId"] == "auth-error-contract-test"


@pytest.mark.asyncio
async def test_bcrypt_admin_password_hash_is_supported() -> None:
    settings = get_settings()
    previous_hash = settings.admin_password_hash
    settings.admin_password_hash = bcrypt.hashpw(b"hashed-development-password", bcrypt.gensalt()).decode()
    try:
        transport = isolated_transport("bcrypt-login")
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            valid = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "hashed-development-password"})
            invalid = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "change-me-in-development"})
    finally:
        settings.admin_password_hash = previous_hash

    assert valid.status_code == 200
    assert invalid.status_code == 401


def test_production_settings_reject_development_defaults() -> None:
    with pytest.raises(ValueError, match="BACKEND_AUTH_SECRET"):
        Settings(environment="production")


def test_password_hash_generator_returns_verifiable_bcrypt_hash() -> None:
    hashed = hash_password("operator-password", rounds=10)

    assert hashed.startswith("$2b$10$")
    assert bcrypt.checkpw(b"operator-password", hashed.encode())


def test_malformed_signed_tokens_are_rejected_without_raising() -> None:
    def token_for(payload: object) -> str:
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        return f"{body}.{_sign(body)}"

    assert verify_admin_token(token_for({"role": "ADMIN", "exp": "not-an-integer"})) is None
    assert verify_team_token(token_for({"role": "TEAM", "exp": True})) is None
    assert verify_admin_token("!!!.invalid") is None
    assert verify_team_token("eyJyb2xlIjoiVEVBTSJ9.%") is None


def test_documented_production_settings_use_only_bcrypt_password_hash() -> None:
    settings = Settings(
        environment="production",
        database_url="mssql+aioodbc://db.example/competition",
        auth_secret="a-production-secret-that-is-at-least-32-characters-long",
        admin_username="competition-operator",
        admin_password_hash=bcrypt.hashpw(b"operator-password", bcrypt.gensalt()).decode(),
        allow_dev_admin=False,
        cors_origins=["https://event.example"],
        trusted_hosts=["api.event.example", "event.example"],
    )

    assert settings.admin_username == "competition-operator"
    assert settings.admin_password_hash is not None


def test_environment_list_settings_accept_csv_and_json_values() -> None:
    csv_settings = Settings(cors_origins="https://event.example", trusted_hosts="api.event.example,event.example")
    json_settings = Settings(cors_origins='["https://event.example"]', trusted_hosts='["api.event.example"]')

    assert csv_settings.cors_origins == ["https://event.example"]
    assert csv_settings.trusted_hosts == ["api.event.example", "event.example"]
    assert json_settings.cors_origins == ["https://event.example"]
    assert json_settings.trusted_hosts == ["api.event.example"]


def test_production_settings_reject_default_username_and_malformed_hash() -> None:
    valid = {
        "environment": "production",
        "database_url": "mssql+aioodbc://db.example/competition",
        "auth_secret": "a-production-secret-that-is-at-least-32-characters-long",
        "admin_password_hash": bcrypt.hashpw(b"operator-password", bcrypt.gensalt()).decode(),
        "allow_dev_admin": False,
        "cors_origins": ["https://event.example"],
        "trusted_hosts": ["api.event.example"],
    }
    with pytest.raises(ValueError, match="BACKEND_ADMIN_USERNAME"):
        Settings(**valid)
    valid["admin_username"] = "competition-operator"
    valid["admin_password_hash"] = "not-a-bcrypt-hash"
    with pytest.raises(ValueError, match="BACKEND_ADMIN_PASSWORD_HASH"):
        Settings(**valid)


@pytest.mark.asyncio
async def test_auth_me_reports_valid_identity_and_rejects_invalid_identity() -> None:
    transport = isolated_transport("auth-me")
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


@pytest.mark.asyncio
async def test_cookie_session_authenticates_and_logout_clears_cookie() -> None:
    transport = isolated_transport("logout")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "change-me-in-development"},
        )
        authenticated = await client.get("/api/v1/auth/me")
        logout = await client.post("/api/v1/auth/logout")
        after_logout = await client.get("/api/v1/auth/me")

    assert login.status_code == 200
    assert authenticated.json()["authenticated"] is True
    assert logout.status_code == 204
    assert after_logout.json()["authenticated"] is False


@pytest.mark.asyncio
async def test_cookie_state_change_rejects_untrusted_origin() -> None:
    transport = isolated_transport("csrf-origin")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "change-me-in-development"},
        )
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "https://evil.example", "x-request-id": "csrf-origin-test"},
        )

    assert login.status_code == 200
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_ORIGIN_REJECTED"
    assert response.json()["requestId"] == "csrf-origin-test"


@pytest.mark.asyncio
async def test_login_rate_limit_is_enforced_from_shared_database_window() -> None:
    transport = ASGITransport(app=app, client=(f"rate-limit-test-{uuid4()}", 43100))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        responses = await asyncio.gather(
            *(client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "change-me-in-development"},
            ) for _ in range(11))
        )

    statuses = [response.status_code for response in responses]
    assert statuses.count(200) == 10
    limited = [response for response in responses if response.status_code == 429]
    assert len(limited) == 1
    assert limited[0].json()["error"]["code"] == "RATE_LIMITED"
