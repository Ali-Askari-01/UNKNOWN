import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import func, select, update

from app.db.models import QuizRealtimeEvent, QuizRealtimeRelayLock
from app.db.session import SessionFactory


class ConnectionManager:
    """Deliver realtime events locally and relay committed events across API workers."""

    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._last_event_id = 0
        self._poll_task: asyncio.Task[None] | None = None
        self._seen_event_ids: set[int] = set()

    async def start(self) -> None:
        if self._poll_task is not None:
            return
        async with SessionFactory() as session:
            latest = await session.scalar(select(func.max(QuizRealtimeEvent.id)))
        self._last_event_id = int(latest or 0)
        self._poll_task = asyncio.create_task(self._poll_events(), name="quiz-realtime-relay")

    async def stop(self) -> None:
        task = self._poll_task
        self._poll_task = None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def connect(self, session_id: UUID, websocket: WebSocket, subprotocol: str | None = None) -> None:
        await websocket.accept(subprotocol=subprotocol)
        self._connections[session_id].add(websocket)

    def disconnect(self, session_id: UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(session_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(session_id, None)

    def health_snapshot(self) -> dict[str, object]:
        task = self._poll_task
        return {
            "relayRunning": task is not None and not task.done(),
            "lastEventId": self._last_event_id,
            "connectionCount": sum(len(connections) for connections in self._connections.values()),
        }

    async def reserve_snapshot_sequence(self, session_id: UUID) -> int:
        async with SessionFactory() as session:
            await self._lock_event_order(session)
            event = QuizRealtimeEvent(
                session_id=session_id,
                event_type="quiz.state.snapshot",
                payload_json="{}",
                should_broadcast=False,
            )
            session.add(event)
            await session.flush()
            sequence = event.id
            await session.commit()
        return sequence

    async def broadcast(self, session_id: UUID, event_type: str, payload: dict[str, Any]) -> None:
        async with SessionFactory() as session:
            await self._lock_event_order(session)
            event = QuizRealtimeEvent(
                session_id=session_id,
                event_type=event_type,
                payload_json=json.dumps(payload, separators=(",", ":"), sort_keys=True),
                should_broadcast=True,
            )
            session.add(event)
            await session.flush()
            event_data = self._event_data(event)
            await session.commit()
        await self._deliver_event(event_data)

    @staticmethod
    async def _lock_event_order(session: Any) -> None:
        """Serialize event ID allocation through transaction commit across workers."""
        result = await session.execute(
            update(QuizRealtimeRelayLock)
            .where(QuizRealtimeRelayLock.id == 1)
            .values(version=QuizRealtimeRelayLock.version + 1)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise RuntimeError("The realtime relay lock row is missing; apply the latest migration.")

    async def _poll_events(self) -> None:
        while True:
            try:
                async with SessionFactory() as session:
                    events = list(
                        (
                            await session.scalars(
                                select(QuizRealtimeEvent)
                                .where(QuizRealtimeEvent.id > self._last_event_id)
                                .order_by(QuizRealtimeEvent.id)
                                .limit(200)
                            )
                        ).all()
                    )
                if events:
                    for event in events:
                        self._last_event_id = max(self._last_event_id, event.id)
                        await self._deliver_event(self._event_data(event))
                else:
                    await asyncio.sleep(0.15)
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(1)

    @staticmethod
    def _event_data(event: QuizRealtimeEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "session_id": event.session_id,
            "event_type": event.event_type,
            "payload": json.loads(event.payload_json),
            "should_broadcast": event.should_broadcast,
            "created_at": event.created_at,
        }

    async def _deliver_event(self, event: dict[str, Any]) -> None:
        event_id = int(event["id"])
        if event_id in self._seen_event_ids or not event["should_broadcast"]:
            return
        self._seen_event_ids.add(event_id)
        if len(self._seen_event_ids) > 10_000:
            self._seen_event_ids = set(sorted(self._seen_event_ids)[-5_000:])

        session_id = event["session_id"]
        connections = list(self._connections.get(session_id, set()))
        if not connections:
            return
        created_at = event["created_at"] or datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        message = {
            "eventId": f"{event['event_type']}-{session_id}-{event_id}",
            "type": event["event_type"],
            "sessionId": str(session_id),
            "sequence": event_id,
            "serverTime": created_at.isoformat(),
            "payload": event["payload"],
        }
        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(session_id, websocket)


connection_manager = ConnectionManager()
