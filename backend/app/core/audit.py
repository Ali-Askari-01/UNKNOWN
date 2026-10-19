import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


def add_audit(
    session: AsyncSession,
    *,
    action_code: str,
    entity_name: str,
    entity_id: UUID | None = None,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditLog(
            action_code=action_code,
            entity_name=entity_name,
            entity_id=entity_id,
            details_json=json.dumps(details or {}, separators=(",", ":")),
        )
    )
