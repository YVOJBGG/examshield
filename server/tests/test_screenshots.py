import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Attempt, Screenshot, User


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
        json={"title": f"M5 Screenshots {uuid.uuid4()}", "time_limit_minutes": 50},
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


@pytest.fixture()
def screenshots_storage_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "screenshots"
    monkeypatch.setattr(settings, "SCREENSHOTS_DIR", str(target))
    return target


def test_student_can_upload_screenshot_for_own_active_attempt(
    client: TestClient,
    auth_tokens: dict[str, str],
    screenshots_storage_dir: Path,
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

        upload_response = client.post(
            "/screenshots/upload",
            headers=_auth_header(student_token),
            data={"attempt_id": attempt_id},
            files={"file": ("capture.png", b"fake-image-bytes", "image/png")},
        )
        assert upload_response.status_code == 201
        payload = upload_response.json()
        assert payload["attempt_id"] == attempt_id
        assert payload["file_path"].startswith(f"{attempt_id}/")
        assert payload["file_url"] == f"/screenshots/{payload['id']}/file"
        assert payload["captured_at"] is not None

        stored_file = screenshots_storage_dir / Path(payload["file_path"])
        assert stored_file.exists()
        assert stored_file.read_bytes() == b"fake-image-bytes"

        with SessionLocal() as db:
            screenshot = db.scalar(select(Screenshot).where(Screenshot.id == payload["id"]))
            assert screenshot is not None
            assert str(screenshot.attempt_id) == attempt_id
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_student_cannot_upload_screenshot_for_another_students_attempt(
    client: TestClient,
    auth_tokens: dict[str, str],
    screenshots_storage_dir: Path,
) -> None:
    _ = screenshots_storage_dir
    admin_token = auth_tokens["admin"]
    owner_token = auth_tokens["student"]
    other_username = f"student_ss_{uuid.uuid4().hex[:8]}"
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

        upload_response = client.post(
            "/screenshots/upload",
            headers=_auth_header(other_token),
            data={"attempt_id": attempt_id},
            files={"file": ("capture.png", b"fake-image-bytes", "image/png")},
        )
        assert upload_response.status_code == 403
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_cannot_upload_screenshot_for_submitted_attempt(
    client: TestClient,
    auth_tokens: dict[str, str],
    screenshots_storage_dir: Path,
) -> None:
    _ = screenshots_storage_dir
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

        upload_response = client.post(
            "/screenshots/upload",
            headers=_auth_header(student_token),
            data={"attempt_id": attempt_id},
            files={"file": ("capture.png", b"fake-image-bytes", "image/png")},
        )
        assert upload_response.status_code == 400
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_admin_can_list_and_view_attempt_screenshots(
    client: TestClient,
    auth_tokens: dict[str, str],
    screenshots_storage_dir: Path,
) -> None:
    _ = screenshots_storage_dir
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

        upload_response = client.post(
            "/screenshots/upload",
            headers=_auth_header(student_token),
            data={"attempt_id": attempt_id},
            files={"file": ("capture.png", b"fake-image-bytes", "image/png")},
        )
        assert upload_response.status_code == 201
        screenshot_id = upload_response.json()["id"]

        list_response = client.get(
            f"/screenshots/attempt/{attempt_id}",
            headers=_auth_header(admin_token),
        )
        assert list_response.status_code == 200
        payload = list_response.json()
        assert len(payload) == 1
        assert payload[0]["id"] == screenshot_id

        file_response = client.get(
            f"/screenshots/{screenshot_id}/file",
            headers=_auth_header(admin_token),
        )
        assert file_response.status_code == 200
        assert file_response.content == b"fake-image-bytes"
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_non_admin_cannot_list_or_view_attempt_screenshots(
    client: TestClient,
    auth_tokens: dict[str, str],
    screenshots_storage_dir: Path,
) -> None:
    _ = screenshots_storage_dir
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

        upload_response = client.post(
            "/screenshots/upload",
            headers=_auth_header(student_token),
            data={"attempt_id": attempt_id},
            files={"file": ("capture.png", b"fake-image-bytes", "image/png")},
        )
        assert upload_response.status_code == 201
        screenshot_id = upload_response.json()["id"]

        list_response = client.get(
            f"/screenshots/attempt/{attempt_id}",
            headers=_auth_header(student_token),
        )
        assert list_response.status_code == 403

        file_response = client.get(
            f"/screenshots/{screenshot_id}/file",
            headers=_auth_header(student_token),
        )
        assert file_response.status_code == 403
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))
