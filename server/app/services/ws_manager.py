import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket

from app.schemas.monitoring import (
    DashboardAttemptSnapshot,
    MonitoringEventEnvelope,
    MonitoringEventOut,
    MonitoringSnapshotEnvelope,
    ViolationBroadcastOut,
    ViolationEnvelope,
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
                existing = self._attempts.get(event.attempt_id)
                self._attempts[event.attempt_id] = DashboardAttemptSnapshot(
                    attempt_id=event.attempt_id,
                    username=event.username,
                    exam_id=event.exam_id,
                    status=event.status,
                    last_event=event.event_type,
                    last_update=event.timestamp,
                    alert_count=0 if existing is None else existing.alert_count,
                    has_alerts=False if existing is None else existing.has_alerts,
                    last_violation_type=None if existing is None else existing.last_violation_type,
                    last_violation_at=None if existing is None else existing.last_violation_at,
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

    async def broadcast_violation(self, violation: ViolationBroadcastOut) -> None:
        stale: list[WebSocket] = []
        violation_envelope = ViolationEnvelope(data=violation)

        async with self._lock:
            existing = self._attempts.get(violation.attempt_id)
            alert_count = 1 if existing is None else existing.alert_count + 1
            self._attempts[violation.attempt_id] = DashboardAttemptSnapshot(
                attempt_id=violation.attempt_id,
                username=violation.username,
                exam_id=violation.exam_id,
                status=violation.status,
                last_event="violation",
                last_update=violation.created_at,
                alert_count=alert_count,
                has_alerts=True,
                last_violation_type=violation.type,
                last_violation_at=violation.created_at,
            )
            sockets = list(self._connections)

        for socket in sockets:
            try:
                await socket.send_json(violation_envelope.model_dump(mode="json"))
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
