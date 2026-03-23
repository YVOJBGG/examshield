import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_exam_with_questions(client: TestClient, admin_token: str) -> tuple[str, str, str]:
    headers = _auth_header(admin_token)
    create_exam_response = client.post(
        "/exams",
        headers=headers,
        json={"title": f"Student Flow Exam {uuid.uuid4()}", "time_limit_minutes": 35},
    )
    assert create_exam_response.status_code == 201
    exam_payload = create_exam_response.json()
    exam_id = exam_payload["id"]
    exam_code = exam_payload["exam_code"]

    create_question_response = client.post(
        f"/exams/{exam_id}/questions",
        headers=headers,
        json={"text": "Explain CAP theorem."},
    )
    assert create_question_response.status_code == 201
    question_id = create_question_response.json()["id"]
    return exam_id, exam_code, question_id


def _ensure_student_user(username: str, password: str) -> None:
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.username == username))
        if existing is not None:
            return
        db.add(User(username=username, password_hash=hash_password(password), role="student"))
        db.commit()


def test_student_exam_execution_flow(client: TestClient, auth_tokens: dict[str, str]) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code, question_id = _create_exam_with_questions(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt = start_response.json()
        attempt_id = attempt["id"]
        assert attempt["status"] == "in_progress"
        assert attempt["submitted_at"] is None
        assert attempt["started_at"] is not None

        # Duplicate active start returns the existing attempt.
        start_again_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert start_again_response.status_code == 200
        assert start_again_response.json()["id"] == attempt_id

        student_exam_response = client.get(
            f"/student/exams/{exam_code}",
            headers=_auth_header(student_token),
        )
        assert student_exam_response.status_code == 200
        student_exam = student_exam_response.json()
        assert student_exam["id"] == exam_id
        assert student_exam["exam_code"] == exam_code
        assert "title" in student_exam
        assert "time_limit_minutes" in student_exam
        assert all({"id", "text"} == set(question.keys()) for question in student_exam["questions"])

        autosave_response = client.post(
            "/answers/autosave",
            headers=_auth_header(student_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Draft answer"}],
            },
        )
        assert autosave_response.status_code == 200
        autosaved = autosave_response.json()
        assert len(autosaved) == 1
        assert autosaved[0]["answer_text"] == "Draft answer"

        autosave_update_response = client.post(
            "/answers/autosave",
            headers=_auth_header(student_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Updated draft"}],
            },
        )
        assert autosave_update_response.status_code == 200
        assert autosave_update_response.json()[0]["answer_text"] == "Updated draft"

        submit_response = client.post(
            "/answers/submit",
            headers=_auth_header(student_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Final answer"}],
            },
        )
        assert submit_response.status_code == 200
        submit_body = submit_response.json()
        assert submit_body["answers_saved"] == 1
        assert submit_body["attempt"]["status"] == "submitted"
        assert submit_body["attempt"]["submitted_at"] is not None

        autosave_after_submit_response = client.post(
            "/answers/autosave",
            headers=_auth_header(student_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Should fail"}],
            },
        )
        assert autosave_after_submit_response.status_code == 400
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_student_exam_lookup_blocks_unavailable_exam_without_active_attempt(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code, _question_id = _create_exam_with_questions(client, admin_token)

    try:
        update_response = client.put(
            f"/exams/{exam_id}",
            headers=_auth_header(admin_token),
            json={"is_available": False},
        )
        assert update_response.status_code == 200

        exam_response = client.get(
            f"/student/exams/{exam_code}",
            headers=_auth_header(student_token),
        )
        assert exam_response.status_code == 400
        assert exam_response.json()["detail"] == "This exam is currently unavailable."
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_student_can_resume_in_progress_attempt_when_exam_becomes_unavailable(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code, _question_id = _create_exam_with_questions(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        update_response = client.put(
            f"/exams/{exam_id}",
            headers=_auth_header(admin_token),
            json={"is_available": False},
        )
        assert update_response.status_code == 200

        exam_response = client.get(
            f"/student/exams/{exam_code}",
            headers=_auth_header(student_token),
        )
        assert exam_response.status_code == 200

        restart_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert restart_response.status_code == 200
        assert restart_response.json()["id"] == attempt_id
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_student_exam_lookup_blocks_reentry_after_submission(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code, question_id = _create_exam_with_questions(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        submit_response = client.post(
            "/answers/submit",
            headers=_auth_header(student_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Final answer"}],
            },
        )
        assert submit_response.status_code == 200

        exam_response = client.get(
            f"/student/exams/{exam_code}",
            headers=_auth_header(student_token),
        )
        assert exam_response.status_code == 400
        assert exam_response.json()["detail"] == (
            "You have already submitted this exam and cannot re-enter it."
        )
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_student_routes_forbid_admin_token(client: TestClient, auth_tokens: dict[str, str]) -> None:
    admin_headers = _auth_header(auth_tokens["admin"])
    random_id = str(uuid.uuid4())

    start_response = client.post("/attempts/start", headers=admin_headers, json={"exam_code": "123456"})
    assert start_response.status_code == 403

    exam_response = client.get(f"/student/exams/{random_id}", headers=admin_headers)
    assert exam_response.status_code == 403

    autosave_response = client.post(
        "/answers/autosave",
        headers=admin_headers,
        json={"attempt_id": random_id, "answers": []},
    )
    assert autosave_response.status_code == 403

    submit_response = client.post(
        "/answers/submit",
        headers=admin_headers,
        json={"attempt_id": random_id, "answers": []},
    )
    assert submit_response.status_code == 403


def test_attempt_ownership_enforced(client: TestClient, auth_tokens: dict[str, str]) -> None:
    _ensure_student_user("student_m3", "student123")
    other_login_response = client.post(
        "/auth/login",
        json={"username": "student_m3", "password": "student123"},
    )
    assert other_login_response.status_code == 200
    other_student_token = other_login_response.json()["access_token"]

    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code, question_id = _create_exam_with_questions(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        other_autosave_response = client.post(
            "/answers/autosave",
            headers=_auth_header(other_student_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Not owner"}],
            },
        )
        assert other_autosave_response.status_code == 403

        other_submit_response = client.post(
            "/answers/submit",
            headers=_auth_header(other_student_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Not owner"}],
            },
        )
        assert other_submit_response.status_code == 403
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))
