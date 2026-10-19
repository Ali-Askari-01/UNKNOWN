import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth import issue_admin_token, verify_admin_token
from app.core.config import get_settings
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    settings = get_settings()
    if not (secrets.compare_digest(payload.username, settings.admin_username) and secrets.compare_digest(payload.password, settings.admin_password)):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return LoginResponse(access_token=issue_admin_token())


@router.get("/me")
async def me(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict[str, object]:
    payload = verify_admin_token(credentials.credentials if credentials else None)
    if payload is None:
        return {"authenticated": False, "role": None, "subject": None}
    return {
        "authenticated": True,
        "role": payload.get("role"),
        "subject": payload.get("sub"),
        "expires_at": payload.get("exp"),
    }
