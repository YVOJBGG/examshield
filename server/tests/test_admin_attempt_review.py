import uuid

from fastapi.testclient import TestClient


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_exam_with_question(client: TestClient, admin_token: str) -> tuple[str, str, str]:
    exam_response = client.post(
        "/exams",
        headers=_auth_header(admin_token),
        json={"title": f"Review Exam {uuid.uuid4()}", "exam_type": "written", "time_limit_minutes": 30},
    )
    assert exam_response.status_code == 201
    exam = exam_response.json()

    question_response = client.post(
        f"/exams/{exam['id']}/questions",
        headers=_auth_header(admin_token),
        json={"text": "Explain idempotency.", "points": 5},
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
        assert payload[0]["grading_state"] == "pending_manual_grading"
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
        assert payload["exam"]["exam_type"] == "written"
        assert payload["score"] is None
        assert payload["grading_state"] == "pending_manual_grading"
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

        detail_response = client.get(
            f"/admin/attempts/{attempt_id}",
            headers=_auth_header(admin_token),
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["grading_state"] == "manually_graded"
    finally:
        client.delete(f"/exams/{exam_id}", headers=_auth_header(admin_token))


def test_admin_can_review_auto_graded_mcq_attempt(client: TestClient, auth_tokens: dict[str, str]) -> None:
    admin_headers = _auth_header(auth_tokens["admin"])
    student_headers = _auth_header(auth_tokens["student"])
    exam_response = client.post(
        "/exams",
        headers=admin_headers,
        json={"title": f"Review MCQ {uuid.uuid4()}", "exam_type": "mcq", "time_limit_minutes": 25},
    )
    assert exam_response.status_code == 201
    exam = exam_response.json()

    question_response = client.post(
        f"/exams/{exam['id']}/questions",
        headers=admin_headers,
        json={
            "text": "Which SQL clause filters rows?",
            "points": 2,
            "options": [
                {"option_text": "WHERE", "is_correct": True},
                {"option_text": "ORDER BY", "is_correct": False},
            ],
        },
    )
    assert question_response.status_code == 201
    question = question_response.json()
    correct_option_id = next(option["id"] for option in question["options"] if option["is_correct"])

    try:
        start_response = client.post(
            "/attempts/start",
            headers=student_headers,
            json={"exam_code": exam["exam_code"]},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        submit_response = client.post(
            "/answers/submit",
            headers=student_headers,
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question["id"], "selected_option_ids": [correct_option_id]}],
            },
        )
        assert submit_response.status_code == 200

        detail_response = client.get(f"/admin/attempts/{attempt_id}", headers=admin_headers)
        assert detail_response.status_code == 200
        payload = detail_response.json()
        assert payload["grading_state"] == "auto_graded"
        assert payload["score"] == 2
        assert payload["answers"][0]["is_correct"] is True
        assert payload["answers"][0]["awarded_points"] == 2
        assert any(option["is_correct"] for option in payload["answers"][0]["options"])
    finally:
        client.delete(f"/exams/{exam['id']}", headers=admin_headers)


def test_manual_grading_is_rejected_for_mcq_attempt(client: TestClient, auth_tokens: dict[str, str]) -> None:
    admin_headers = _auth_header(auth_tokens["admin"])
    student_headers = _auth_header(auth_tokens["student"])
    exam_response = client.post(
        "/exams",
        headers=admin_headers,
        json={"title": f"MCQ Manual Reject {uuid.uuid4()}", "exam_type": "mcq", "time_limit_minutes": 25},
    )
    assert exam_response.status_code == 201
    exam = exam_response.json()

    question_response = client.post(
        f"/exams/{exam['id']}/questions",
        headers=admin_headers,
        json={
            "text": "Which command lists rows?",
            "options": [
                {"option_text": "SELECT", "is_correct": True},
                {"option_text": "DELETE", "is_correct": False},
            ],
        },
    )
    assert question_response.status_code == 201
    question = question_response.json()
    correct_option_id = next(option["id"] for option in question["options"] if option["is_correct"])

    try:
        start_response = client.post(
            "/attempts/start",
            headers=student_headers,
            json={"exam_code": exam["exam_code"]},
        )
        assert start_response.status_code == 200
        attempt_id = start_response.json()["id"]

        submit_response = client.post(
            "/answers/submit",
            headers=student_headers,
            json={
                "attempt_id": attempt_id,
                "answers": [{"question_id": question["id"], "selected_option_ids": [correct_option_id]}],
            },
        )
        assert submit_response.status_code == 200

        score_response = client.put(
            f"/admin/attempts/{attempt_id}/score",
            headers=admin_headers,
            json={"score": 1},
        )
        assert score_response.status_code == 400
    finally:
        client.delete(f"/exams/{exam['id']}", headers=admin_headers)


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
