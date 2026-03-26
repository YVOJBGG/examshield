import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Attempt, User, Violation
from app.services.ws_manager import admin_monitoring_manager


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _create_exam_with_question(client: TestClient, admin_token: str) -> tuple[str, str]:
    response = client.post(
        "/exams",
        headers=_auth_header(admin_token),
        json={"title": f"M5 Violations {uuid.uuid4()}", "exam_type": "written", "time_limit_minutes": 50},
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["id"], payload["exam_code"]


def _ensure_student_user(username: str, password: str) -> None:
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.username == username))
        if existing is not None:
            return
        db.add(User(username=username, password_hash=hash_password(password), role="student"))
        db.commit()


@pytest.fixture(autouse=True)
def reset_monitoring_manager_state() -> None:
    admin_monitoring_manager._attempts.clear()
    admin_monitoring_manager._connections.clear()


def test_student_can_create_violation_for_own_active_attempt(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code = _create_exam_with_question(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        create_response = client.post(
            "/violations",
            headers=_auth_header(student_token),
            json={
                "attempt_id": attempt_id,
                "type": "focus_lost",
                "details": "Window lost focus during exam",
            },
        )
        assert create_response.status_code == 201
        payload = create_response.json()
        assert payload["attempt_id"] == attempt_id
        assert payload["type"] == "focus_lost"
        assert payload["details"] == "Window lost focus during exam"
        assert payload["created_at"] is not None

        with SessionLocal() as db:
            violation = db.scalar(select(Violation).where(Violation.id == payload["id"]))
            assert violation is not None
            assert str(violation.attempt_id) == attempt_id
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_student_can_create_shortcut_violation_for_own_active_attempt(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code = _create_exam_with_question(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        create_response = client.post(
            "/violations",
            headers=_auth_header(student_token),
            json={
                "attempt_id": attempt_id,
                "type": "desktop_switch_attempt",
                "details": "Detected Windows+Ctrl+Right shortcut attempt during exam",
            },
        )
        assert create_response.status_code == 201
        payload = create_response.json()
        assert payload["attempt_id"] == attempt_id
        assert payload["type"] == "desktop_switch_attempt"
        assert payload["details"] == "Detected Windows+Ctrl+Right shortcut attempt during exam"

        with SessionLocal() as db:
            violation = db.scalar(select(Violation).where(Violation.id == payload["id"]))
            assert violation is not None
            assert violation.type == "desktop_switch_attempt"
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_student_cannot_create_violation_for_another_students_attempt(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    owner_token = auth_tokens["student"]
    other_username = f"student_m5_{uuid.uuid4().hex[:8]}"
    _ensure_student_user(other_username, "student123")
    other_token = _login(client, other_username, "student123")
    exam_id, exam_code = _create_exam_with_question(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(owner_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        create_response = client.post(
            "/violations",
            headers=_auth_header(other_token),
            json={"attempt_id": attempt_id, "type": "manual_flag", "details": "Not owner"},
        )
        assert create_response.status_code == 403
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_cannot_create_violation_for_submitted_attempt(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code = _create_exam_with_question(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        with SessionLocal() as db:
            attempt = db.scalar(select(Attempt).where(Attempt.id == attempt_id))
            assert attempt is not None
            attempt.status = "submitted"
            db.commit()

        create_response = client.post(
            "/violations",
            headers=_auth_header(student_token),
            json={"attempt_id": attempt_id, "type": "window_switch", "details": "After submit"},
        )
        assert create_response.status_code == 400
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_admin_can_list_attempt_violations(client: TestClient, auth_tokens: dict[str, str]) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code = _create_exam_with_question(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        create_response = client.post(
            "/violations",
            headers=_auth_header(student_token),
            json={"attempt_id": attempt_id, "type": "forbidden_key", "details": "Alt+Tab"},
        )
        assert create_response.status_code == 201

        list_response = client.get(
            f"/violations/attempt/{attempt_id}",
            headers=_auth_header(admin_token),
        )
        assert list_response.status_code == 200
        payload = list_response.json()
        assert len(payload) == 1
        assert payload[0]["id"] == create_response.json()["id"]
        assert payload[0]["type"] == "forbidden_key"

        student_list_response = client.get(
            f"/violations/attempt/{attempt_id}",
            headers=_auth_header(student_token),
        )
        assert student_list_response.status_code == 403
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_violation_broadcast_updates_snapshot_and_pushes_admin_socket(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code = _create_exam_with_question(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        monitoring_response = client.post(
            "/monitoring/status",
            headers=_auth_header(student_token),
            json={
                "event_type": "in_exam",
                "exam_id": exam_id,
                "attempt_id": attempt_id,
                "status": "in_progress",
                "message": "Student in exam",
            },
        )
        assert monitoring_response.status_code == 200

        with client.websocket_connect(f"/ws/admin/monitor?token={admin_token}") as websocket:
            snapshot_message = websocket.receive_json()
            assert snapshot_message["type"] == "snapshot"
            assert snapshot_message["attempts"][0]["attempt_id"] == attempt_id
            assert snapshot_message["attempts"][0]["alert_count"] == 0
            assert snapshot_message["attempts"][0]["has_alerts"] is False

            create_response = client.post(
                "/violations",
                headers=_auth_header(student_token),
                json={
                    "attempt_id": attempt_id,
                    "type": "tab_switch_attempt",
                    "details": "Detected Ctrl+Tab shortcut attempt during exam",
                },
            )
            assert create_response.status_code == 201

            violation_message = websocket.receive_json()
            assert violation_message["type"] == "violation"
            assert violation_message["data"]["attempt_id"] == attempt_id
            assert violation_message["data"]["type"] == "tab_switch_attempt"
            assert violation_message["data"]["exam_id"] == exam_id
            assert violation_message["data"]["status"] == "in_progress"

        attempts = list(admin_monitoring_manager._attempts.values())
        assert len(attempts) == 1
        snapshot = attempts[0]
        assert str(snapshot.attempt_id) == attempt_id
        assert snapshot.alert_count == 1
        assert snapshot.has_alerts is True
        assert snapshot.last_violation_type == "tab_switch_attempt"
        assert snapshot.last_violation_at is not None
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))
