import pytest
from fastapi.testclient import TestClient


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    return body["access_token"]


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("admin", "admin123"),
        ("student1", "student123"),
    ],
)
def test_login_success(
    client: TestClient, ensure_auth_users: None, username: str, password: str
) -> None:
    token = login(client, username, password)
    assert token


def test_auth_me_for_logged_in_user(client: TestClient, ensure_auth_users: None) -> None:
    token = login(client, "student1", "student123")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "student1"
    assert body["role"] == "student"
    assert body["id"]


def test_admin_ping_allows_admin_and_blocks_student(client: TestClient, ensure_auth_users: None) -> None:
    admin_token = login(client, "admin", "admin123")
    student_token = login(client, "student1", "student123")

    admin_response = client.get("/admin/ping", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_response.status_code == 200

    student_response = client.get("/admin/ping", headers={"Authorization": f"Bearer {student_token}"})
    assert student_response.status_code == 403
