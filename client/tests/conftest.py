from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def client_data_dir(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("EXAMSHIELD_CLIENT_DATA_DIR", str(tmp_path))
    return tmp_path


class FakeNetworkClient:
    def __init__(self) -> None:
        self.login_response: dict[str, Any] = {"access_token": "token-123"}
        self.exam_payload: dict[str, Any] | None = None
        self.start_attempt_payload: dict[str, Any] = {
            "id": "attempt-1",
            "started_at": "2026-04-14T08:00:00+00:00",
        }
        self.autosave_response: list[dict[str, Any]] = [{"ok": True}]
        self.submit_response: dict[str, Any] = {"attempt": {"status": "submitted"}}
        self.raise_on_autosave: Exception | None = None
        self.raise_on_submit: Exception | None = None
        self.reported_violations: list[dict[str, Any]] = []
        self.monitoring_events: list[dict[str, Any]] = []
        self.uploads: list[dict[str, Any]] = []
        self.cleared_token = False

    def login(self, username: str, password: str) -> dict[str, Any]:
        return self.login_response

    def clear_token(self) -> None:
        self.cleared_token = True

    def get_student_exam(self, exam_code: str) -> dict[str, Any]:
        assert self.exam_payload is not None
        return self.exam_payload

    def start_attempt(self, exam_code: str) -> dict[str, Any]:
        return self.start_attempt_payload

    def autosave_answers(self, attempt_id: str, answers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.raise_on_autosave is not None:
            raise self.raise_on_autosave
        return self.autosave_response

    def submit_answers(self, attempt_id: str, answers: list[dict[str, Any]]) -> dict[str, Any]:
        if self.raise_on_submit is not None:
            raise self.raise_on_submit
        return self.submit_response

    def send_monitoring_status(
        self,
        *,
        event_type: str,
        exam_id: str,
        attempt_id: str,
        status: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "event_type": event_type,
            "exam_id": exam_id,
            "attempt_id": attempt_id,
            "status": status,
            "message": message,
        }
        self.monitoring_events.append(payload)
        return payload

    def report_violation(
        self,
        *,
        attempt_id: str,
        violation_type: str,
        details: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "attempt_id": attempt_id,
            "violation_type": violation_type,
            "details": details,
        }
        self.reported_violations.append(payload)
        return payload

    def upload_screenshot(
        self,
        *,
        attempt_id: str,
        filename: str,
        content: bytes,
        content_type: str = "image/png",
    ) -> dict[str, Any]:
        payload = {
            "attempt_id": attempt_id,
            "filename": filename,
            "content": content,
            "content_type": content_type,
        }
        self.uploads.append(payload)
        return payload


@pytest.fixture
def fake_network_client() -> FakeNetworkClient:
    return FakeNetworkClient()
