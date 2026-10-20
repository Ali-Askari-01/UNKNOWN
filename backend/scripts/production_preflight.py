"""Validate release configuration and database state without printing secrets.

This is intentionally an executable release check rather than an application
health endpoint: it can fail a deployment before workers are started.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import get_settings
from app.core.release import EXPECTED_MIGRATION_HEAD


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-head",
        default=EXPECTED_MIGRATION_HEAD,
        help="Alembic revision that must be installed (default: %(default)s)",
    )
    parser.add_argument(
        "--base-url",
        help="Optional running service URL; checks /health/ready when supplied",
    )
    parser.add_argument(
        "--allow-development",
        action="store_true",
        help="Permit local development settings; never use this for a production release",
    )
    return parser.parse_args()


def validate_settings(*, allow_development: bool) -> list[str]:
    settings = get_settings()
    errors: list[str] = []
    if not allow_development and settings.environment != "production":
        errors.append("BACKEND_ENVIRONMENT must be production")
    if settings.database_url.startswith("sqlite") and not allow_development:
        errors.append("BACKEND_DATABASE_URL must not use SQLite")
    if settings.auth_secret == "development-only-change-this-secret" and not allow_development:
        errors.append("BACKEND_AUTH_SECRET is using the development default")
    if not settings.admin_password_hash and not allow_development:
        errors.append("BACKEND_ADMIN_PASSWORD_HASH is not configured")
    if settings.allow_dev_admin and not allow_development:
        errors.append("BACKEND_ALLOW_DEV_ADMIN must be false")
    if not settings.cors_origins:
        errors.append("BACKEND_CORS_ORIGINS must contain at least one origin")
    elif not allow_development and settings.cors_origins == ["http://localhost:3000"]:
        errors.append("BACKEND_CORS_ORIGINS is using the development default")
    if not settings.trusted_hosts:
        errors.append("BACKEND_TRUSTED_HOSTS must contain at least one host")
    elif not allow_development and settings.trusted_hosts == ["localhost", "127.0.0.1", "test"]:
        errors.append("BACKEND_TRUSTED_HOSTS is using the development default")
    return errors


async def read_database_revision(engine: AsyncEngine) -> str | None:
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT version_num FROM alembic_version"))
        row = result.first()
        return str(row[0]) if row else None


def check_running_service(base_url: str) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/health/ready"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            status = response.status
            return status == 200, f"service readiness HTTP {status}"
    except HTTPError as exc:
        return False, f"service readiness HTTP {exc.code}"
    except URLError as exc:
        return False, f"service readiness unavailable ({exc.reason})"
    except TimeoutError:
        return False, "service readiness timed out"


async def run() -> int:
    args = parse_args()
    try:
        errors = validate_settings(allow_development=args.allow_development)
    except Exception as exc:  # noqa: BLE001 - release check must report a safe summary
        print(f"FAIL config: {type(exc).__name__}")
        return 1
    if errors:
        for error in errors:
            print(f"FAIL config: {error}")
        return 1

    from app.db.session import engine, ping_database

    try:
        await ping_database()
        print("PASS database connectivity")
        revision = await read_database_revision(engine)
        if revision != args.expected_head:
            print(f"FAIL migration head: expected {args.expected_head}, found {revision or 'none'}")
            return 1
        print(f"PASS migration head: {revision}")
        from app.core.schema_contract import find_schema_contract_errors

        schema_errors = await find_schema_contract_errors(engine)
        if schema_errors:
            for error in schema_errors:
                print(f"FAIL schema contract: {error}")
            return 1
        print("PASS FastAPI-owned schema contract")
    except Exception as exc:  # noqa: BLE001 - release check must report a safe summary
        print(f"FAIL database preflight: {type(exc).__name__}")
        return 1
    finally:
        await engine.dispose()

    if args.base_url:
        ok, message = check_running_service(args.base_url)
        print(f"{'PASS' if ok else 'FAIL'} {message}")
        if not ok:
            return 1

    print("PASS production preflight")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
