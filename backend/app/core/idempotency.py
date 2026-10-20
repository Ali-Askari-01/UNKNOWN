import hashlib
import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import IdempotencyRecord


def request_hash(payload: object) -> str:
    """Return a stable hash for a JSON-compatible request payload."""
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def validate_key(key: str | None) -> str | None:
    if key is None:
        return None
    if not 1 <= len(key) <= 128 or any(ord(char) < 32 for char in key):
        raise AppError("INVALID_IDEMPOTENCY_KEY", "The Idempotency-Key header is invalid.", 400)
    return key


async def reserve(
    session: AsyncSession,
    *,
    scope_key: str,
    key: str | None,
    payload_hash: str,
) -> IdempotencyRecord | None:
    """Reserve a retry key or return its completed record.

    A unique database constraint arbitrates concurrent first requests. A caller that observes a
    record without a response must not execute the mutation twice.
    """
    key = validate_key(key)
    if key is None:
        return None

    record = await session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.scope_key == scope_key,
            IdempotencyRecord.idempotency_key == key,
        )
    )
    if record is not None:
        if record.request_hash != payload_hash:
            raise AppError("IDEMPOTENCY_KEY_REUSED", "The Idempotency-Key was used with a different request.", 409)
        if not record.response_json:
            raise AppError("IDEMPOTENCY_IN_PROGRESS", "The original request is still being processed.", 409)
        return record

    record = IdempotencyRecord(scope_key=scope_key, idempotency_key=key, request_hash=payload_hash)
    try:
        async with session.begin_nested():
            session.add(record)
            await session.flush()
    except IntegrityError:
        record = await session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.scope_key == scope_key,
                IdempotencyRecord.idempotency_key == key,
            )
        )
        if record is None or not record.response_json:
            raise AppError("IDEMPOTENCY_IN_PROGRESS", "The original request is still being processed.", 409)
        if record.request_hash != payload_hash:
            raise AppError("IDEMPOTENCY_KEY_REUSED", "The Idempotency-Key was used with a different request.", 409)
    return record
