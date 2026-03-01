import uuid

import pytest
from fastapi.testclient import TestClient


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_exam(client: TestClient, admin_token: str) -> str:
    response = client.post(
        "/exams",
        headers=_auth_header(admin_token),
        json={"title": f"Question CRUD Exam {uuid.uuid4()}", "time_limit_minutes": 50},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_admin_questions_crud_flow(client: TestClient, auth_tokens: dict[str, str]) -> None:
    admin_token = auth_tokens["admin"]
    admin_headers = _auth_header(admin_token)
    exam_id = _create_exam(client, admin_token)

    try:
        create_response = client.post(
            f"/exams/{exam_id}/questions",
            headers=admin_headers,
            json={"text": "What is normalization?"},
        )
        assert create_response.status_code == 201
        question = create_response.json()
        question_id = question["id"]
        assert question["exam_id"] == exam_id

        list_response = client.get(f"/exams/{exam_id}/questions", headers=admin_headers)
        assert list_response.status_code == 200
        assert any(item["id"] == question_id for item in list_response.json())

        get_response = client.get(f"/exams/{exam_id}/questions/{question_id}", headers=admin_headers)
        assert get_response.status_code == 200
        assert get_response.json()["id"] == question_id

        update_response = client.put(
            f"/exams/{exam_id}/questions/{question_id}",
            headers=admin_headers,
            json={"text": "Define normalization in DBMS."},
        )
        assert update_response.status_code == 200
        assert update_response.json()["text"] == "Define normalization in DBMS."

        delete_response = client.delete(f"/exams/{exam_id}/questions/{question_id}", headers=admin_headers)
        assert delete_response.status_code == 204

        confirm_response = client.get(f"/exams/{exam_id}/questions/{question_id}", headers=admin_headers)
        assert confirm_response.status_code == 404
    finally:
        client.delete(f"/exams/{exam_id}", headers=admin_headers)


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", f"/exams/{uuid.uuid4()}/questions", None),
        ("post", f"/exams/{uuid.uuid4()}/questions", {"text": "Denied question"}),
        ("get", f"/exams/{uuid.uuid4()}/questions/{uuid.uuid4()}", None),
        ("put", f"/exams/{uuid.uuid4()}/questions/{uuid.uuid4()}", {"text": "Denied update"}),
        ("delete", f"/exams/{uuid.uuid4()}/questions/{uuid.uuid4()}", None),
    ],
)
def test_student_forbidden_for_question_operations(
    client: TestClient, auth_tokens: dict[str, str], method: str, path: str, body: dict | None
) -> None:
    student_headers = _auth_header(auth_tokens["student"])
    response = client.request(method=method.upper(), url=path, headers=student_headers, json=body)
    assert response.status_code == 403


def test_question_not_found_returns_404(client: TestClient, auth_tokens: dict[str, str]) -> None:
    admin_token = auth_tokens["admin"]
    admin_headers = _auth_header(admin_token)
    exam_id = _create_exam(client, admin_token)
    missing_question_id = uuid.uuid4()

    try:
        get_response = client.get(
            f"/exams/{exam_id}/questions/{missing_question_id}",
            headers=admin_headers,
        )
        assert get_response.status_code == 404

        put_response = client.put(
            f"/exams/{exam_id}/questions/{missing_question_id}",
            headers=admin_headers,
            json={"text": "Missing"},
        )
        assert put_response.status_code == 404

        delete_response = client.delete(
            f"/exams/{exam_id}/questions/{missing_question_id}",
            headers=admin_headers,
        )
        assert delete_response.status_code == 404
    finally:
        client.delete(f"/exams/{exam_id}", headers=admin_headers)


def test_question_endpoints_return_404_when_exam_missing(
    client: TestClient, auth_tokens: dict[str, str]
) -> None:
    admin_headers = _auth_header(auth_tokens["admin"])
    missing_exam_id = uuid.uuid4()

    list_response = client.get(f"/exams/{missing_exam_id}/questions", headers=admin_headers)
    assert list_response.status_code == 404

    create_response = client.post(
        f"/exams/{missing_exam_id}/questions",
        headers=admin_headers,
        json={"text": "Does not matter"},
    )
    assert create_response.status_code == 404
