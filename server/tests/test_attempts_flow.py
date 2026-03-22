import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Answer, User


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _create_exam_with_question(client: TestClient, admin_token: str) -> tuple[str, str, str]:
    headers = _auth_header(admin_token)
    exam_response = client.post(
        "/exams",
        headers=headers,
        json={"title": f"M3 Attempt Flow {uuid.uuid4()}", "time_limit_minutes": 45},
    )
    assert exam_response.status_code == 201
    exam_payload = exam_response.json()
    exam_id = exam_payload["id"]
    exam_code = exam_payload["exam_code"]

    question_response = client.post(
        f"/exams/{exam_id}/questions",
        headers=headers,
        json={"text": "What is eventual consistency?"},
    )
    assert question_response.status_code == 201
    question_id = question_response.json()["id"]
    return exam_id, exam_code, question_id


def _ensure_student_user(username: str, password: str) -> None:
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.username == username))
        if existing is not None:
            return
        db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                role="student",
            )
        )
        db.commit()


def test_student_full_attempt_flow_success(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = _login(client, "student1", "student123")
    exam_id, exam_code, question_id = _create_exam_with_question(client, admin_token)

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
        assert attempt["started_at"] is not None
        assert attempt["submitted_at"] is None

        exam_response = client.get(
            f"/student/exams/{exam_code}",
            headers=_auth_header(student_token),
        )
        assert exam_response.status_code == 200
        exam_payload = exam_response.json()
        assert exam_payload["id"] == exam_id
        assert exam_payload["exam_code"] == exam_code
        assert "title" in exam_payload
        assert "time_limit_minutes" in exam_payload
        assert isinstance(exam_payload["questions"], list)
        assert any(item["id"] == question_id for item in exam_payload["questions"])
        assert all(set(item.keys()) == {"id", "text"} for item in exam_payload["questions"])

        autosave_response = client.post(
            "/answers/autosave",
            headers=_auth_header(student_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Draft"}],
            },
        )
        assert autosave_response.status_code == 200
        autosaved = autosave_response.json()
        assert len(autosaved) == 1
        assert autosaved[0]["attempt_id"] == attempt_id
        assert autosaved[0]["question_id"] == question_id
        assert autosaved[0]["answer_text"] == "Draft"

        submit_response = client.post(
            "/answers/submit",
            headers=_auth_header(student_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Final"}],
            },
        )
        assert submit_response.status_code == 200
        submit_payload = submit_response.json()
        assert submit_payload["answers_saved"] == 1
        assert submit_payload["attempt"]["status"] == "submitted"
        assert submit_payload["attempt"]["submitted_at"] is not None
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_autosave_rejected_after_submit(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code, question_id = _create_exam_with_question(client, admin_token)

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
                "answers": [{"question_id": question_id, "answer_text": "Done"}],
            },
        )
        assert submit_response.status_code == 200

        autosave_after_submit = client.post(
            "/answers/autosave",
            headers=_auth_header(student_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Should fail"}],
            },
        )
        assert autosave_after_submit.status_code == 400
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_student_cannot_write_another_students_attempt(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    owner_token = auth_tokens["student"]

    other_username = f"student_m3_{uuid.uuid4().hex[:8]}"
    _ensure_student_user(other_username, "student123")
    other_token = _login(client, other_username, "student123")
    exam_id, exam_code, question_id = _create_exam_with_question(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(owner_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        autosave_other = client.post(
            "/answers/autosave",
            headers=_auth_header(other_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Not owner"}],
            },
        )
        assert autosave_other.status_code == 403

        submit_other = client.post(
            "/answers/submit",
            headers=_auth_header(other_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Not owner"}],
            },
        )
        assert submit_other.status_code == 403
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_admin_cannot_use_student_only_endpoints(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_headers = _auth_header(auth_tokens["admin"])
    random_id = str(uuid.uuid4())

    start_response = client.post(
        "/attempts/start",
        headers=admin_headers,
        json={"exam_code": "123456"},
    )
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


def test_start_attempt_nonexistent_exam_returns_404(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    response = client.post(
        "/attempts/start",
        headers=_auth_header(auth_tokens["student"]),
        json={"exam_code": "999999"},
    )
    assert response.status_code == 404


def test_autosave_and_submit_nonexistent_attempt_return_404(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code, question_id = _create_exam_with_question(client, admin_token)
    missing_attempt_id = str(uuid.uuid4())

    try:
        autosave_response = client.post(
            "/answers/autosave",
            headers=_auth_header(student_token),
            json={
                "attempt_id": missing_attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "x"}],
            },
        )
        assert autosave_response.status_code == 404

        submit_response = client.post(
            "/answers/submit",
            headers=_auth_header(student_token),
            json={
                "attempt_id": missing_attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "y"}],
            },
        )
        assert submit_response.status_code == 404
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_repeated_autosave_updates_existing_answer_row(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, question_id = _create_exam_with_question(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        first_autosave = client.post(
            "/answers/autosave",
            headers=_auth_header(student_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Version 1"}],
            },
        )
        assert first_autosave.status_code == 200
        first_answer_id = first_autosave.json()[0]["id"]

        second_autosave = client.post(
            "/answers/autosave",
            headers=_auth_header(student_token),
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question_id, "answer_text": "Version 2"}],
            },
        )
        assert second_autosave.status_code == 200
        second_payload = second_autosave.json()[0]
        assert second_payload["id"] == first_answer_id
        assert second_payload["answer_text"] == "Version 2"

        with SessionLocal() as db:
            rows = list(
                db.scalars(
                    select(Answer).where(
                        Answer.attempt_id == attempt_id,
                        Answer.question_id == question_id,
                    )
                ).all()
            )
            assert len(rows) == 1
            assert rows[0].answer_text == "Version 2"
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))
