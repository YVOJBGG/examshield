import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket

from app.schemas.monitoring import (
    DashboardAttemptSnapshot,
    MonitoringEventEnvelope,
    MonitoringEventOut,
    MonitoringSnapshotEnvelope,
)


class AdminMonitoringConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._attempts: dict[uuid.UUID, DashboardAttemptSnapshot] = {}
        self._lock = asyncio.Lock()

    async def connect_admin(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
            snapshot = self._build_snapshot_locked()
        await websocket.send_json(snapshot.model_dump(mode="json"))

    async def disconnect_admin(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast_event(self, event: MonitoringEventOut) -> None:
        stale: list[WebSocket] = []
        event_envelope = MonitoringEventEnvelope(data=event)
        is_terminal = event.event_type in {"submitted", "disconnected"} or event.status in {
            "submitted",
            "cancelled",
        }

        async with self._lock:
            if is_terminal:
                self._attempts.pop(event.attempt_id, None)
            else:
                self._attempts[event.attempt_id] = DashboardAttemptSnapshot(
                    attempt_id=event.attempt_id,
                    username=event.username,
                    exam_id=event.exam_id,
                    status=event.status,
                    last_event=event.event_type,
                    last_update=event.timestamp,
                )
            sockets = list(self._connections)

        for socket in sockets:
            try:
                await socket.send_json(event_envelope.model_dump(mode="json"))
            except Exception:
                stale.append(socket)

        if stale:
            async with self._lock:
                for socket in stale:
                    self._connections.discard(socket)

    def _build_snapshot_locked(self) -> MonitoringSnapshotEnvelope:
        now = datetime.now(timezone.utc)
        attempts = sorted(
            self._attempts.values(),
            key=lambda item: item.last_update or now,
            reverse=True,
        )
        return MonitoringSnapshotEnvelope(attempts=attempts)


admin_monitoring_manager = AdminMonitoringConnectionManager()
