from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.db.models import AuditLog
from app.db.session import get_db_session

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/admin/audit-log")
async def list_audit_log(
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    _: dict[str, object] = Depends(require_admin),
) -> list[dict[str, object]]:
    rows = (await session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))).all()
    return [
        {
            "id": row.id,
            "actionCode": row.action_code,
            "entityName": row.entity_name,
            "entityId": str(row.entity_id) if row.entity_id else None,
            "details": row.details_json,
            "createdAt": row.created_at.isoformat() if isinstance(row.created_at, datetime) else None,
        }
        for row in rows
    ]
