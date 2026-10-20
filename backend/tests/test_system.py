import asyncio

import pytest
import bcrypt
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.db.models import QuizRealtimeEvent, QuizRealtimeRelayLock, QuizSession
from app.db.session import SessionFactory, initialize_local_database
import app.db.session as db_session
from app.main import app
from app.realtime.manager import ConnectionManager


@pytest.fixture(autouse=True)
async def initialize_test_database() -> None:
    await initialize_local_database()


class FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def accept(self, subprotocol: str | None = None) -> None:
        return None

    async def send_json(self, message: dict[str, object]) -> None:
        self.messages.append(message)


@pytest.mark.asyncio
async def test_system_status_reports_migration_state() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "fastapi"
    assert payload["apiVersion"] == "v1"
    assert payload["realtime"] == "native-websocket"


@pytest.mark.asyncio
async def test_production_sql_server_uses_bounded_connection_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        environment="production",
        database_url="mssql+aioodbc://user:password@localhost/competition?driver=ODBC+Driver+18+for+SQL+Server",
        auth_secret="production-secret-for-pool-test-that-is-long-enough",
        admin_username="competition-operator",
        admin_password_hash=bcrypt.hashpw(b"operator-password", bcrypt.gensalt()).decode(),
        allow_dev_admin=False,
        cors_origins=["https://event.example"],
        trusted_hosts=["api.event.example"],
        db_pool_size=7,
        db_max_overflow=11,
        db_pool_timeout=19,
        db_pool_recycle=1200,
    )
    monkeypatch.setattr(db_session, "get_settings", lambda: settings)

    production_engine = db_session.create_engine()
    try:
        assert not isinstance(production_engine.pool, NullPool)
        assert production_engine.pool.size() == 7
        assert production_engine.pool._max_overflow == 11
    finally:
        await production_engine.dispose()


@pytest.mark.asyncio
async def test_realtime_events_relay_between_worker_managers() -> None:
    async with SessionFactory() as session:
        session_id = await session.scalar(select(QuizSession.id).limit(1))
    assert session_id is not None

    local_manager = ConnectionManager()
    publishing_manager = ConnectionManager()
    socket = FakeWebSocket()
    await local_manager.start()
    await publishing_manager.start()
    await local_manager.connect(session_id, socket)
    try:
        await publishing_manager.broadcast(session_id, "quiz.test.relay", {"value": "cross-worker"})
        for _ in range(20):
            if socket.messages:
                break
            await asyncio.sleep(0.1)
        assert socket.messages
        assert socket.messages[0]["type"] == "quiz.test.relay"
        assert socket.messages[0]["payload"] == {"value": "cross-worker"}
    finally:
        local_manager.disconnect(session_id, socket)
        await local_manager.stop()
        await publishing_manager.stop()
        async with SessionFactory() as session:
            await session.execute(delete(QuizRealtimeEvent).where(QuizRealtimeEvent.event_type == "quiz.test.relay"))
            await session.commit()


@pytest.mark.asyncio
async def test_realtime_event_ids_follow_transaction_commit_order() -> None:
    async with SessionFactory() as lookup:
        session_id = await lookup.scalar(select(QuizSession.id).limit(1))
    assert session_id is not None

    first_type = "quiz.test.order.first"
    second_type = "quiz.test.order.second"
    first_transaction = SessionFactory()
    publisher = ConnectionManager()
    second_write: asyncio.Task[None] | None = None
    try:
        await publisher._lock_event_order(first_transaction)
        first_transaction.add(
            QuizRealtimeEvent(
                session_id=session_id,
                event_type=first_type,
                payload_json="{}",
                should_broadcast=True,
            )
        )
        await first_transaction.flush()

        second_write = asyncio.create_task(publisher.broadcast(session_id, second_type, {}))
        await asyncio.sleep(0.1)
        assert not second_write.done()

        await first_transaction.commit()
        await asyncio.wait_for(second_write, timeout=5)

        async with SessionFactory() as verification:
            rows = list(
                (
                    await verification.scalars(
                        select(QuizRealtimeEvent)
                        .where(QuizRealtimeEvent.event_type.in_([first_type, second_type]))
                        .order_by(QuizRealtimeEvent.id)
                    )
                ).all()
            )
            lock_row = await verification.get(QuizRealtimeRelayLock, 1)
            await verification.execute(delete(QuizRealtimeEvent).where(QuizRealtimeEvent.event_type.in_([first_type, second_type])))
            await verification.commit()
    finally:
        if second_write is not None and not second_write.done():
            second_write.cancel()
            await asyncio.gather(second_write, return_exceptions=True)
        await first_transaction.rollback()
        await first_transaction.close()

    assert [row.event_type for row in rows] == [first_type, second_type]
    assert lock_row is not None and lock_row.version >= 2
