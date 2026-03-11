from __future__ import annotations

from app.services.network_client import NetworkClient


class MonitoringClient:
    def __init__(self, network_client: NetworkClient) -> None:
        self._network_client = network_client
        self._exam_id: str | None = None
        self._attempt_id: str | None = None
        self._last_ok = False
        self._last_error: str | None = None

    def set_session(self, *, exam_id: str, attempt_id: str) -> None:
        self._exam_id = exam_id
        self._attempt_id = attempt_id

    def clear_session(self) -> None:
        self._exam_id = None
        self._attempt_id = None

    @property
    def is_available(self) -> bool:
        return self._last_ok

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def send_connected(self, status: str = "in_progress", message: str | None = None) -> bool:
        return self._send_event("connected", status=status, message=message)

    def send_in_exam(self, status: str = "in_progress", message: str | None = None) -> bool:
        return self._send_event("in_exam", status=status, message=message)

    def send_autosave(self, status: str = "in_progress", message: str | None = None) -> bool:
        return self._send_event("autosave", status=status, message=message)

    def send_submitted(self, status: str = "submitted", message: str | None = None) -> bool:
        return self._send_event("submitted", status=status, message=message)

    def send_disconnected(self, status: str = "in_progress", message: str | None = None) -> bool:
        return self._send_event("disconnected", status=status, message=message)

    def send_heartbeat(self, status: str = "in_progress", message: str | None = None) -> bool:
        return self.send_in_exam(status=status, message=message)

    def _send_event(self, event_type: str, *, status: str, message: str | None) -> bool:
        if not self._exam_id or not self._attempt_id:
            self._last_ok = False
            self._last_error = "Monitoring session is not initialized"
            return False
        try:
            self._network_client.send_monitoring_status(
                event_type=event_type,
                exam_id=self._exam_id,
                attempt_id=self._attempt_id,
                status=status,
                message=message,
            )
            self._last_ok = True
            self._last_error = None
            return True
        except Exception as exc:
            self._last_ok = False
            self._last_error = str(exc)
            return False
