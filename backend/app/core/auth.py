import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

bearer = HTTPBearer(auto_error=False)


def _encode(data: dict[str, object]) -> str:
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _sign(value: str) -> str:
    return hmac.new(get_settings().auth_secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def issue_admin_token() -> str:
    payload = {"sub": get_settings().admin_username, "role": "ADMIN", "exp": int(time.time()) + 8 * 60 * 60, "nonce": secrets.token_hex(8)}
    body = _encode(payload)
    return f"{body}.{_sign(body)}"


def verify_admin_token(token: str | None) -> dict[str, object] | None:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(signature, _sign(body)):
        return None
    try:
        padding = "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(body + padding))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("role") != "ADMIN" or int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


async def require_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict[str, object]:
    settings = get_settings()
    if settings.environment == "development" and settings.allow_dev_admin and credentials is None:
        return {"sub": "local-development", "role": "ADMIN"}
    payload = verify_admin_token(credentials.credentials if credentials else None)
    if payload is None:
        raise HTTPException(status_code=401, detail="Administrator authentication required.")
    return payload
