from __future__ import annotations

import pytest

from app.services.violation_service import ViolationService


def test_violation_service_reports_success_and_updates_status(fake_network_client) -> None:
    service = ViolationService(fake_network_client)

    ok = service.report_violation("attempt-1", "focus_lost", "Window lost focus")

    assert ok is True
    assert service.is_available is True
    assert service.last_error is None
    assert service.last_status_message == "Violation sent: focus_lost"
    assert fake_network_client.reported_violations == [
        {
            "attempt_id": "attempt-1",
            "violation_type": "focus_lost",
            "details": "Window lost focus",
        }
    ]


def test_violation_service_returns_false_and_records_error_on_failure(fake_network_client) -> None:
    service = ViolationService(fake_network_client)

    def fail_report(**kwargs):
        raise RuntimeError("backend unavailable")

    fake_network_client.report_violation = fail_report

    ok = service.report_violation("attempt-1", "focus_lost", "Window lost focus")

    assert ok is False
    assert service.is_available is False
    assert service.last_error == "backend unavailable"
    assert service.last_status_message == "Violation send failed: focus_lost"


def test_violation_service_cooldown_suppresses_duplicate_reports(
    fake_network_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timestamps = iter([100.0, 101.0, 106.5])
    monkeypatch.setattr("app.services.violation_service.time.monotonic", lambda: next(timestamps))
    service = ViolationService(fake_network_client)

    first = service.report_focus_lost("attempt-1")
    second = service.report_focus_lost("attempt-1")
    third = service.report_focus_lost("attempt-1")

    assert first is True
    assert second is False
    assert third is True
    assert service.last_status_message == "Violation sent: focus_lost"
    assert len(fake_network_client.reported_violations) == 2
