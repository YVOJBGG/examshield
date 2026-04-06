import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Answer, Attempt, Exam, Screenshot, User, Violation


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_user(*, username_prefix: str) -> User:
    with SessionLocal() as db:
        user = User(
            username=f"{username_prefix}_{uuid.uuid4().hex[:8]}",
            password_hash=hash_password("student123"),
            role="student",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def _create_written_exam(client: TestClient, admin_token: str) -> tuple[dict, dict]:
    exam_response = client.post(
        "/exams",
        headers=_auth_header(admin_token),
        json={"title": f"Analytics Written {uuid.uuid4()}", "exam_type": "written", "time_limit_minutes": 40},
    )
    assert exam_response.status_code == 201
    exam = exam_response.json()

    question_response = client.post(
        f"/exams/{exam['id']}/questions",
        headers=_auth_header(admin_token),
        json={"text": "Explain ACID.", "points": 5},
    )
    assert question_response.status_code == 201
    return exam, question_response.json()


def _create_mcq_exam(client: TestClient, admin_token: str) -> tuple[dict, list[dict]]:
    exam_response = client.post(
        "/exams",
        headers=_auth_header(admin_token),
        json={"title": f"Analytics MCQ {uuid.uuid4()}", "exam_type": "mcq", "time_limit_minutes": 20},
    )
    assert exam_response.status_code == 201
    exam = exam_response.json()

    question_one = client.post(
        f"/exams/{exam['id']}/questions",
        headers=_auth_header(admin_token),
        json={
            "text": "Which SQL clause filters rows?",
            "points": 2,
            "options": [
                {"option_text": "WHERE", "is_correct": True},
                {"option_text": "ORDER BY", "is_correct": False},
            ],
        },
    )
    assert question_one.status_code == 201

    question_two = client.post(
        f"/exams/{exam['id']}/questions",
        headers=_auth_header(admin_token),
        json={
            "text": "Which command inserts data?",
            "points": 2,
            "options": [
                {"option_text": "INSERT", "is_correct": True},
                {"option_text": "DROP", "is_correct": False},
            ],
        },
    )
    assert question_two.status_code == 201
    return exam, [question_one.json(), question_two.json()]


def test_admin_can_end_exam_and_force_submit_active_attempts(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam, _question = _create_written_exam(client, admin_token)

    try:
        start_response = client.post(
            "/attempts/start",
            headers=_auth_header(student_token),
            json={"exam_code": exam["exam_code"]},
        )
        assert start_response.status_code == 200
        active_attempt_id = start_response.json()["id"]

        other_student = _create_user(username_prefix="analytics_end")
        with SessionLocal() as db:
            submitted_attempt = Attempt(
                user_id=other_student.id,
                exam_id=uuid.UUID(exam["id"]),
                status="submitted",
                started_at=datetime.now(timezone.utc) - timedelta(minutes=15),
                submitted_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            )
            db.add(submitted_attempt)
            db.commit()

        response = client.post(
            f"/admin/exams/{exam['id']}/end",
            headers=_auth_header(admin_token),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["exam_id"] == exam["id"]
        assert payload["updated_attempts"] == 1
        assert payload["already_completed_attempts"] == 1
        assert payload["status"] == "ended"
        assert payload["ended_at"] is not None

        with SessionLocal() as db:
            stored_exam = db.get(Exam, uuid.UUID(exam["id"]))
            stored_active_attempt = db.get(Attempt, uuid.UUID(active_attempt_id))
            assert stored_exam is not None
            assert stored_exam.is_ended is True
            assert stored_exam.ended_at is not None
            assert stored_active_attempt is not None
            assert stored_active_attempt.status == "force_submitted"
            assert stored_active_attempt.submitted_at is not None
    finally:
        client.delete(f"/exams/{exam['id']}", headers=_auth_header(admin_token))


def test_non_admin_cannot_access_exam_end_or_analytics(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    student_token = auth_tokens["student"]
    exam, _question = _create_written_exam(client, admin_token)

    try:
        end_response = client.post(
            f"/admin/exams/{exam['id']}/end",
            headers=_auth_header(student_token),
        )
        assert end_response.status_code == 403

        analytics_response = client.get(
            f"/admin/exams/{exam['id']}/analytics",
            headers=_auth_header(student_token),
        )
        assert analytics_response.status_code == 403
    finally:
        client.delete(f"/exams/{exam['id']}", headers=_auth_header(admin_token))


def test_exam_end_and_analytics_return_404_for_missing_exam(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_headers = _auth_header(auth_tokens["admin"])
    missing_exam_id = uuid.uuid4()

    end_response = client.post(f"/admin/exams/{missing_exam_id}/end", headers=admin_headers)
    assert end_response.status_code == 404

    analytics_response = client.get(f"/admin/exams/{missing_exam_id}/analytics", headers=admin_headers)
    assert analytics_response.status_code == 404


def test_analytics_handles_exam_with_no_attempts_gracefully(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    exam, question = _create_written_exam(client, admin_token)

    try:
        response = client.get(
            f"/admin/exams/{exam['id']}/analytics",
            headers=_auth_header(admin_token),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["exam"]["exam_id"] == exam["id"]
        assert payload["exam"]["total_attempts"] == 0
        assert payload["exam"]["completed_attempts"] == 0
        assert payload["exam"]["submission_rate_percent"] == 0.0
        assert payload["exam"]["average_violations_per_attempt"] == 0.0
        assert payload["questions"][0]["question_id"] == question["id"]
        assert payload["questions"][0]["total_answers"] == 0
        assert payload["questions"][0]["unanswered_count"] == 0
        assert payload["metadata"]["question_time_method"] == "approx_saved_at_deltas"
        assert payload["metadata"]["question_alert_method"] == "not_available"
    finally:
        client.delete(f"/exams/{exam['id']}", headers=_auth_header(admin_token))


def test_analytics_returns_structured_exam_and_question_stats(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_token = auth_tokens["admin"]
    exam, questions = _create_mcq_exam(client, admin_token)
    exam_id = uuid.UUID(exam["id"])
    first_question_id = uuid.UUID(questions[0]["id"])
    second_question_id = uuid.UUID(questions[1]["id"])
    q1_correct = next(option["id"] for option in questions[0]["options"] if option["is_correct"])
    q1_wrong = next(option["id"] for option in questions[0]["options"] if not option["is_correct"])
    q2_correct = next(option["id"] for option in questions[1]["options"] if option["is_correct"])
    student_one = _create_user(username_prefix="analytics_mcq_a")
    student_two = _create_user(username_prefix="analytics_mcq_b")
    started_one = datetime.now(timezone.utc) - timedelta(minutes=20)
    started_two = datetime.now(timezone.utc) - timedelta(minutes=18)

    try:
        with SessionLocal() as db:
            attempt_one = Attempt(
                user_id=student_one.id,
                exam_id=exam_id,
                status="submitted",
                started_at=started_one,
                submitted_at=started_one + timedelta(minutes=10),
                score=4,
                graded_at=started_one + timedelta(minutes=10),
            )
            attempt_two = Attempt(
                user_id=student_two.id,
                exam_id=exam_id,
                status="force_submitted",
                started_at=started_two,
                submitted_at=started_two + timedelta(minutes=12),
                score=2,
                graded_at=started_two + timedelta(minutes=12),
            )
            db.add_all([attempt_one, attempt_two])
            db.flush()

            db.add_all(
                [
                    Answer(
                        attempt_id=attempt_one.id,
                        question_id=first_question_id,
                        selected_option_ids=[q1_correct],
                        saved_at=started_one + timedelta(minutes=2),
                    ),
                    Answer(
                        attempt_id=attempt_one.id,
                        question_id=second_question_id,
                        selected_option_ids=[q2_correct],
                        saved_at=started_one + timedelta(minutes=5),
                    ),
                    Answer(
                        attempt_id=attempt_two.id,
                        question_id=first_question_id,
                        selected_option_ids=[q1_wrong],
                        saved_at=started_two + timedelta(minutes=3),
                    ),
                ]
            )
            db.add_all(
                [
                    Violation(
                        attempt_id=attempt_one.id,
                        type="focus_lost",
                        details="Lost focus once",
                    ),
                    Violation(
                        attempt_id=attempt_two.id,
                        type="focus_lost",
                        details="Lost focus twice",
                    ),
                    Violation(
                        attempt_id=attempt_two.id,
                        type="focus_lost",
                        details="Second violation",
                    ),
                    Screenshot(
                        attempt_id=attempt_one.id,
                        file_path="screenshots/a1.png",
                    ),
                ]
            )
            exam_row = db.get(Exam, exam_id)
            assert exam_row is not None
            exam_row.is_ended = True
            exam_row.ended_at = datetime.now(timezone.utc)
            db.commit()

        response = client.get(
            f"/admin/exams/{exam['id']}/analytics",
            headers=_auth_header(admin_token),
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["exam"]["exam_id"] == exam["id"]
        assert payload["exam"]["exam_title"] == exam["title"]
        assert payload["exam"]["total_attempts"] == 2
        assert payload["exam"]["completed_attempts"] == 2
        assert payload["exam"]["force_submitted_attempts"] == 1
        assert payload["exam"]["submission_rate_percent"] == 100.0
        assert payload["exam"]["total_violations"] == 3
        assert payload["exam"]["total_screenshots"] == 1
        assert payload["exam"]["most_common_violation_type"] == "focus_lost"
        assert payload["exam"]["attempts_with_violations_percent"] == 100.0
        assert payload["exam"]["average_questions_answered_per_attempt"] == 1.5
        assert payload["exam"]["hardest_question"]["question_id"] == questions[0]["id"]

        question_items = {item["question_id"]: item for item in payload["questions"]}
        assert question_items[questions[0]["id"]]["total_answers"] == 2
        assert question_items[questions[0]["id"]]["unanswered_count"] == 0
        assert question_items[questions[0]["id"]]["average_time_spent_seconds"] is not None
        assert question_items[questions[0]["id"]]["correct_rate_percent"] == 50.0
        assert len(question_items[questions[0]["id"]]["mcq_option_distribution"]) == 2

        assert question_items[questions[1]["id"]]["total_answers"] == 1
        assert question_items[questions[1]["id"]]["unanswered_count"] == 1
        assert question_items[questions[1]["id"]]["correct_rate_percent"] == 100.0
        assert payload["metadata"]["question_time_method"] == "approx_saved_at_deltas"
        assert payload["metadata"]["question_alert_method"] == "not_available"
    finally:
        client.delete(f"/exams/{exam['id']}", headers=_auth_header(admin_token))
