from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.session import ping_database

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> JSONResponse:
    try:
        await ping_database()
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "unavailable"})
    return JSONResponse(status_code=200, content={"status": "ok", "database": "ok"})
