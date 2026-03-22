import uuid

import pytest
from fastapi.testclient import TestClient


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_exams_crud_flow(client: TestClient, auth_tokens: dict[str, str]) -> None:
    admin_headers = _auth_header(auth_tokens["admin"])
    unique_title = f"Exam CRUD {uuid.uuid4()}"

    create_response = client.post(
        "/exams",
        headers=admin_headers,
        json={"title": unique_title, "time_limit_minutes": 30},
    )
    assert create_response.status_code == 201
    exam = create_response.json()
    exam_id = exam["id"]
    assert exam["title"] == unique_title
    assert exam["time_limit_minutes"] == 30
    assert exam["exam_code"].isdigit()
    assert len(exam["exam_code"]) == 6

    list_response = client.get("/exams", headers=admin_headers)
    assert list_response.status_code == 200
    assert any(item["id"] == exam_id for item in list_response.json())

    get_response = client.get(f"/exams/{exam_id}", headers=admin_headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == exam_id

    update_response = client.put(
        f"/exams/{exam_id}",
        headers=admin_headers,
        json={"title": f"{unique_title} Updated", "time_limit_minutes": 45},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"].endswith("Updated")
    assert update_response.json()["time_limit_minutes"] == 45

    delete_response = client.delete(f"/exams/{exam_id}", headers=admin_headers)
    assert delete_response.status_code == 204

    confirm_response = client.get(f"/exams/{exam_id}", headers=admin_headers)
    assert confirm_response.status_code == 404


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/exams", None),
        ("post", "/exams", {"title": "Denied Exam", "time_limit_minutes": 20}),
        ("get", f"/exams/{uuid.uuid4()}", None),
        ("put", f"/exams/{uuid.uuid4()}", {"title": "Denied", "time_limit_minutes": 10}),
        ("delete", f"/exams/{uuid.uuid4()}", None),
    ],
)
def test_student_forbidden_for_exam_operations(
    client: TestClient, auth_tokens: dict[str, str], method: str, path: str, body: dict | None
) -> None:
    student_headers = _auth_header(auth_tokens["student"])
    response = client.request(method=method.upper(), url=path, headers=student_headers, json=body)
    assert response.status_code == 403


def test_exam_not_found_returns_404(client: TestClient, auth_tokens: dict[str, str]) -> None:
    admin_headers = _auth_header(auth_tokens["admin"])
    missing_id = uuid.uuid4()

    get_response = client.get(f"/exams/{missing_id}", headers=admin_headers)
    assert get_response.status_code == 404

    put_response = client.put(
        f"/exams/{missing_id}",
        headers=admin_headers,
        json={"title": "Missing", "time_limit_minutes": 10},
    )
    assert put_response.status_code == 404

    delete_response = client.delete(f"/exams/{missing_id}", headers=admin_headers)
    assert delete_response.status_code == 404
