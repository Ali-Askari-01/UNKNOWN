from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError
from app.db.models import RateLimitBucket, RateLimitEvent
from app.db.session import SessionFactory


def request_bucket_key(request: Request, bucket: str, identity: str | None = None) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{bucket}:{identity or client_host}"


async def enforce_rate_limit(
    request: Request,
    bucket: str,
    limit: int,
    window_seconds: float,
    identity: str | None = None,
) -> None:
    """Enforce a shared sliding-window limit using the configured database.

    The event table is deliberately separate from request business transactions. This ensures a
    rejected or later-rolled-back request still counts against abuse controls and that all API
    workers observe the same window.
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=window_seconds)
    bucket_key = request_bucket_key(request, bucket, identity)

    for _ in range(2):
        try:
            async with SessionFactory() as session, session.begin():
                bucket_query = (
                    select(RateLimitBucket)
                    .where(RateLimitBucket.bucket_key == bucket_key)
                    .with_hint(RateLimitBucket, "WITH (UPDLOCK, ROWLOCK)", dialect_name="mssql")
                )
                bucket_row = await session.scalar(bucket_query)
                if bucket_row is None:
                    session.add(RateLimitBucket(bucket_key=bucket_key))
                    await session.flush()

                await session.execute(
                    delete(RateLimitEvent).where(
                        RateLimitEvent.bucket_key == bucket_key,
                        RateLimitEvent.occurred_at < cutoff,
                    )
                )
                event_count = await session.scalar(
                    select(func.count(RateLimitEvent.id)).where(
                        RateLimitEvent.bucket_key == bucket_key,
                        RateLimitEvent.occurred_at >= cutoff,
                    )
                )
                if int(event_count or 0) >= limit:
                    rate_limited = True
                else:
                    rate_limited = False
                    session.add(RateLimitEvent(bucket_key=bucket_key, occurred_at=now))
            if rate_limited:
                raise AppError("RATE_LIMITED", "Too many requests. Please try again shortly.", 429)
            return
        except IntegrityError:
            # Another worker created the bucket between our lookup and insert. Retry so the
            # next transaction can acquire its row lock and evaluate the shared window.
            continue

    raise AppError("RATE_LIMITED", "Rate-limit coordination is busy. Please try again shortly.", 429)
