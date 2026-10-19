from fastapi import APIRouter

from app.core.config import get_settings


router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/system/status")
async def system_status() -> dict[str, object]:
    settings = get_settings()
    return {
        "service": "fastapi",
        "apiVersion": "v1",
        "environment": settings.environment,
        "databaseConfigured": bool(settings.database_url),
        "realtime": "socketio-compatibility-bridge",
        "frontendMigration": "fastapi-data-plane-connected",
    }
