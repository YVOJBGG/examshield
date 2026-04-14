from app.services.monitoring_client import MonitoringClient


def test_monitoring_client_requires_session_before_sending(fake_network_client) -> None:
    client = MonitoringClient(fake_network_client)

    ok = client.send_connected()

    assert ok is False
    assert client.is_available is False
    assert client.last_error == "Monitoring session is not initialized"


def test_monitoring_client_sends_session_bound_events(fake_network_client) -> None:
    client = MonitoringClient(fake_network_client)
    client.set_session(exam_id="exam-1", attempt_id="attempt-1")

    ok = client.send_autosave(message="Draft synced")

    assert ok is True
    assert client.is_available is True
    assert fake_network_client.monitoring_events == [
        {
            "event_type": "autosave",
            "exam_id": "exam-1",
            "attempt_id": "attempt-1",
            "status": "in_progress",
            "message": "Draft synced",
        }
    ]


def test_monitoring_client_clears_session(fake_network_client) -> None:
    client = MonitoringClient(fake_network_client)
    client.set_session(exam_id="exam-1", attempt_id="attempt-1")

    client.clear_session()

    assert client.send_submitted() is False
