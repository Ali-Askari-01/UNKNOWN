import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

bearer = HTTPBearer(auto_error=False)
ADMIN_COOKIE_NAME = "unknown_admin_session"
TEAM_COOKIE_NAME = "unknown_team_session"


def _encode(data: dict[str, object]) -> str:
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _sign(value: str) -> str:
    return hmac.new(get_settings().auth_secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def _decode_payload(token: str | None) -> dict[str, object] | None:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    if not body or not hmac.compare_digest(signature, _sign(body)):
        return None
    try:
        padding = "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(body + padding))
    except (ValueError, TypeError, json.JSONDecodeError, binascii.Error):
        return None
    return payload if isinstance(payload, dict) else None


def issue_admin_token() -> str:
    payload = {"sub": get_settings().admin_username, "role": "ADMIN", "exp": int(time.time()) + 8 * 60 * 60, "nonce": secrets.token_hex(8)}
    body = _encode(payload)
    return f"{body}.{_sign(body)}"


def verify_admin_token(token: str | None) -> dict[str, object] | None:
    payload = _decode_payload(token)
    if payload is None:
        return None
    exp = payload.get("exp")
    if payload.get("role") != "ADMIN" or type(exp) is not int or exp < int(time.time()):
        return None
    return payload


def issue_team_token(*, session_id: str, participant_id: str, team_id: str) -> str:
    payload = {
        "sub": team_id,
        "role": "TEAM",
        "session_id": session_id,
        "participant_id": participant_id,
        "exp": int(time.time()) + 8 * 60 * 60,
        "nonce": secrets.token_hex(8),
    }
    body = _encode(payload)
    return f"{body}.{_sign(body)}"


def verify_team_token(token: str | None) -> dict[str, object] | None:
    payload = _decode_payload(token)
    if payload is None:
        return None
    exp = payload.get("exp")
    if payload.get("role") != "TEAM" or type(exp) is not int or exp < int(time.time()):
        return None
    if not all(isinstance(payload.get(key), str) for key in ("sub", "session_id", "participant_id")):
        return None
    return payload


async def require_admin(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict[str, object]:
    settings = get_settings()
    token = credentials.credentials if credentials else request.cookies.get(ADMIN_COOKIE_NAME)
    if settings.environment == "development" and settings.allow_dev_admin and token is None:
        return {"sub": "local-development", "role": "ADMIN"}
    payload = verify_admin_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Administrator authentication required.")
    return payload


async def require_team(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict[str, object]:
    token = credentials.credentials if credentials else request.cookies.get(TEAM_COOKIE_NAME)
    payload = verify_team_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Team authentication required.")
    return payload
