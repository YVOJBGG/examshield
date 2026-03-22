import uuid

from fastapi.testclient import TestClient


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_exam_with_question(client: TestClient, admin_token: str) -> tuple[str, str, str]:
    exam_response = client.post(
        "/exams",
        headers=_auth_header(admin_token),
        json={"title": f"Review Exam {uuid.uuid4()}", "time_limit_minutes": 30},
    )
    assert exam_response.status_code == 201
    exam = exam_response.json()

    question_response = client.post(
        f"/exams/{exam['id']}/questions",
        headers=_auth_header(admin_token),
        json={"text": "Explain idempotency."},
    )
    assert question_response.status_code == 201
    return exam["id"], exam["exam_code"], question_response.json()["id"]


def _create_submitted_attempt(
    client: TestClient,
    *,
    admin_token: str,
    student_token: str,
) -> tuple[str, str, str]:
    exam_id, exam_code, question_id = _create_exam_with_question(client, admin_token)

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
            "answers": [{"question_id": question_id, "answer_text": "Safe retry without duplicates"}],
        },
    )
    assert submit_response.status_code == 200
    return exam_id, attempt_id, question_id


def test_admin_can_list_submitted_attempts_for_exam(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, attempt_id, _question_id = _create_submitted_attempt(
        client,
        admin_token=admin_token,
        student_token=student_token,
    )

    try:
        response = client.get(
            f"/admin/exams/{exam_id}/attempts",
            headers=_auth_header(admin_token),
        )
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["attempt_id"] == attempt_id
        assert payload[0]["status"] == "submitted"
        assert payload[0]["score"] is None
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_admin_can_fetch_attempt_review_detail(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, attempt_id, question_id = _create_submitted_attempt(
        client,
        admin_token=admin_token,
        student_token=student_token,
    )

    try:
        response = client.get(
            f"/admin/attempts/{attempt_id}",
            headers=_auth_header(admin_token),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["attempt_id"] == attempt_id
        assert payload["status"] == "submitted"
        assert payload["student"]["username"] == "student1"
        assert payload["exam"]["id"] == exam_id
        assert payload["score"] is None
        assert any(item["question_id"] == question_id for item in payload["answers"])
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_admin_can_assign_and_update_score(client: TestClient, auth_tokens: dict[str, str]) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, attempt_id, _question_id = _create_submitted_attempt(
        client,
        admin_token=admin_token,
        student_token=student_token,
    )

    try:
        first_response = client.put(
            f"/admin/attempts/{attempt_id}/score",
            headers=_auth_header(admin_token),
            json={"score": 18},
        )
        assert first_response.status_code == 200
        assert first_response.json()["score"] == 18
        assert first_response.json()["graded_at"] is not None

        second_response = client.put(
            f"/admin/attempts/{attempt_id}/score",
            headers=_auth_header(admin_token),
            json={"score": 19.5},
        )
        assert second_response.status_code == 200
        assert second_response.json()["score"] == 19.5
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_non_admin_cannot_access_attempt_review_endpoints(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, attempt_id, _question_id = _create_submitted_attempt(
        client,
        admin_token=admin_token,
        student_token=student_token,
    )

    try:
        list_response = client.get(
            f"/admin/exams/{exam_id}/attempts",
            headers=_auth_header(student_token),
        )
        assert list_response.status_code == 403

        detail_response = client.get(
            f"/admin/attempts/{attempt_id}",
            headers=_auth_header(student_token),
        )
        assert detail_response.status_code == 403

        score_response = client.put(
            f"/admin/attempts/{attempt_id}/score",
            headers=_auth_header(student_token),
            json={"score": 10},
        )
        assert score_response.status_code == 403
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_scoring_in_progress_attempt_is_rejected(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam_id, exam_code, _question_id = _create_exam_with_question(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam_code},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        score_response = client.put(
            f"/admin/attempts/{attempt_id}/score",
            headers=_auth_header(admin_token),
            json={"score": 7},
        )
        assert score_response.status_code == 400
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))
