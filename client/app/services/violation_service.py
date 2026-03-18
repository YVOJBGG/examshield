from __future__ import annotations

import time

from app.config import FOCUS_LOST_VIOLATION_COOLDOWN_SECONDS
from app.services.network_client import NetworkClient


class ViolationService:
    def __init__(self, network_client: NetworkClient) -> None:
        self._network_client = network_client
        self._last_ok = False
        self._last_error: str | None = None
        self._last_status_message = "Violation reporting idle"
        self._cooldowns: dict[tuple[str, str], float] = {}

    @property
    def is_available(self) -> bool:
        return self._last_ok

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def last_status_message(self) -> str:
        return self._last_status_message

    def report_violation(self, attempt_id: str, violation_type: str, details: str | None = None) -> bool:
        try:
            self._network_client.report_violation(
                attempt_id=attempt_id,
                violation_type=violation_type,
                details=details,
            )
            self._last_ok = True
            self._last_error = None
            self._last_status_message = f"Violation sent: {violation_type}"
            return True
        except Exception as exc:
            self._last_ok = False
            self._last_error = str(exc)
            self._last_status_message = f"Violation send failed: {violation_type}"
            return False

    def report_focus_lost(self, attempt_id: str) -> bool:
        key = (attempt_id, "focus_lost")
        now = time.monotonic()
        last_sent = self._cooldowns.get(key)
        if last_sent is not None and now - last_sent < FOCUS_LOST_VIOLATION_COOLDOWN_SECONDS:
            self._last_status_message = "Focus loss ignored during cooldown"
            return False
        ok = self.report_violation(
            attempt_id,
            "focus_lost",
            "Exam window lost focus during active attempt",
        )
        if ok:
            self._cooldowns[key] = now
        return ok

    def report_manual_flag(self, attempt_id: str, details: str | None = None) -> bool:
        message = details or "Manual test violation triggered from client"
        return self.report_violation(attempt_id, "manual_flag", message)
