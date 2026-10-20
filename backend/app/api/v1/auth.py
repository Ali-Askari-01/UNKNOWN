import secrets
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import ADMIN_COOKIE_NAME, TEAM_COOKIE_NAME, issue_admin_token, issue_team_token, verify_admin_token
from app.core.audit import add_audit
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.idempotency import request_hash, reserve
from app.core.rate_limit import enforce_rate_limit
from app.db.models import ClassTrack, QuizBlueprint, QuizParticipant, QuizSession, Team, TeamClass
from app.db.session import get_db_session
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.participation import TeamJoinRequest, TeamJoinResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


def verify_admin_password(password: str) -> bool:
    settings = get_settings()
    if settings.admin_password_hash:
        try:
            return bcrypt.checkpw(password.encode(), settings.admin_password_hash.encode())
        except ValueError:
            return False
    return settings.environment == "development" and secrets.compare_digest(password, settings.admin_password)


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request, response: Response) -> LoginResponse:
    await enforce_rate_limit(request, "login", limit=10, window_seconds=60)
    settings = get_settings()
    if not (secrets.compare_digest(payload.username, settings.admin_username) and verify_admin_password(payload.password)):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = issue_admin_token()
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        max_age=8 * 60 * 60,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        path="/",
    )
    return LoginResponse(access_token=token)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    response.delete_cookie(key=ADMIN_COOKIE_NAME, path="/")
    response.delete_cookie(key=TEAM_COOKIE_NAME, path="/")


@router.post("/team/join", response_model=TeamJoinResponse, status_code=201)
async def team_join(
    payload: TeamJoinRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> TeamJoinResponse:
    await enforce_rate_limit(request, "team-join", limit=30, window_seconds=60)
    result = await session.execute(
        select(QuizSession, QuizBlueprint, ClassTrack)
        .join(QuizBlueprint, QuizBlueprint.id == QuizSession.blueprint_id)
        .join(ClassTrack, ClassTrack.id == QuizBlueprint.class_track_id)
        .where(QuizSession.quiz_code == payload.quiz_code.strip().upper())
    )
    row = result.first()
    team = await session.scalar(select(Team).where(Team.id == payload.team_id))
    if row is None or team is None:
        raise AppError("INVALID_TEAM_JOIN", "The quiz code or team was not found.", 404)
    quiz_session, _, class_track = row
    linked = await session.scalar(
        select(TeamClass).where(TeamClass.team_id == team.id, TeamClass.class_track_id == class_track.id)
    )
    if quiz_session.status not in {"WAITING", "ACTIVE"} or linked is None or team.event_edition_id != class_track.event_edition_id:
        raise AppError("INVALID_TEAM_JOIN", "This team cannot join the selected quiz session.", 409)

    idempotency_record = await reserve(
        session,
        scope_key=f"team-join:{quiz_session.id}:{team.id}",
        key=request.headers.get("Idempotency-Key"),
        payload_hash=request_hash(payload.model_dump(mode="json")),
    )
    if idempotency_record is not None and idempotency_record.response_json:
        replay = TeamJoinResponse.model_validate_json(idempotency_record.response_json)
        response.set_cookie(
            key=TEAM_COOKIE_NAME,
            value=replay.access_token,
            max_age=8 * 60 * 60,
            httponly=True,
            secure=get_settings().environment == "production",
            samesite="lax",
            path="/",
        )
        return replay

    participant = await session.scalar(
        select(QuizParticipant).where(
            QuizParticipant.quiz_session_id == quiz_session.id,
            QuizParticipant.team_id == team.id,
            QuizParticipant.left_at.is_(None),
        )
    )
    if participant is None:
        participant = QuizParticipant(quiz_session_id=quiz_session.id, team_id=team.id)
        session.add(participant)
        await session.flush()
        add_audit(
            session,
            action_code="PARTICIPANT_REGISTERED",
            entity_name="quiz_participant",
            entity_id=participant.id,
            details={"session_id": str(quiz_session.id), "team_id": str(team.id)},
        )

    token = issue_team_token(
        session_id=str(quiz_session.id), participant_id=str(participant.id), team_id=str(team.id)
    )
    response.set_cookie(
        key=TEAM_COOKIE_NAME,
        value=token,
        max_age=8 * 60 * 60,
        httponly=True,
        secure=get_settings().environment == "production",
        samesite="lax",
        path="/",
    )
    result = TeamJoinResponse(
        id=participant.id,
        quiz_session_id=participant.quiz_session_id,
        team_id=participant.team_id,
        access_token=token,
    )
    if idempotency_record is not None:
        idempotency_record.response_json = result.model_dump_json()
    await session.commit()
    return result


@router.get("/me")
async def me(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict[str, object]:
    token = credentials.credentials if credentials else request.cookies.get(ADMIN_COOKIE_NAME)
    payload = verify_admin_token(token)
    if payload is None:
        return {"authenticated": False, "role": None, "subject": None}
    return {
        "authenticated": True,
        "role": payload.get("role"),
        "subject": payload.get("sub"),
        "expires_at": payload.get("exp"),
    }
