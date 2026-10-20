from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.release import EXPECTED_MIGRATION_HEAD
from app.db.session import get_schema_revision, ping_database
from app.realtime.manager import connection_manager

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> JSONResponse:
    realtime = connection_manager.health_snapshot()
    try:
        await ping_database()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "unavailable", "realtime": realtime},
        )
    if get_settings().environment == "production":
        try:
            revision = await get_schema_revision()
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "migration": "unavailable", "realtime": realtime},
            )
        if revision != EXPECTED_MIGRATION_HEAD:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "migration": "out_of_date", "realtime": realtime},
            )
    if get_settings().environment == "production" and not realtime["relayRunning"]:
        return JSONResponse(status_code=503, content={"status": "unavailable", "realtime": realtime})
    return JSONResponse(status_code=200, content={"status": "ok", "database": "ok", "realtime": realtime})
