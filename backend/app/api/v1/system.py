from fastapi import APIRouter

from app.core.config import get_settings
from app.realtime.manager import connection_manager


router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/system/status")
async def system_status() -> dict[str, object]:
    settings = get_settings()
    return {
        "service": "fastapi",
        "apiVersion": "v1",
        "environment": settings.environment,
        "databaseConfigured": bool(settings.database_url),
        "realtime": "native-websocket",
        "realtimeRelay": connection_manager.health_snapshot(),
        "workers": settings.workers,
        "frontendMigration": "fastapi-data-plane-connected",
    }
