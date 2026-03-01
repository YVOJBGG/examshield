import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models import User
from app.scripts.seed import USERS as SEEDED_USERS


def _seeded_user(role: str) -> dict[str, str]:
    for user in SEEDED_USERS:
        if user["role"] == role:
            return user
    raise RuntimeError(f"No seeded user found for role={role}")


ADMIN_USER = _seeded_user("admin")
STUDENT_USER = _seeded_user("student")
USERS = [ADMIN_USER, STUDENT_USER]


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def ensure_auth_users() -> None:
    with SessionLocal() as db:
        for item in USERS:
            existing = db.scalar(select(User).where(User.username == item["username"]))
            if existing:
                continue
            db.add(
                User(
                    username=item["username"],
                    password_hash=hash_password(item["password"]),
                    role=item["role"],
                )
            )
        db.commit()


@pytest.fixture(scope="session")
def auth_tokens(client: TestClient, ensure_auth_users: None) -> dict[str, str]:
    admin_response = client.post(
        "/auth/login",
        json={"username": ADMIN_USER["username"], "password": ADMIN_USER["password"]},
    )
    assert admin_response.status_code == 200
    admin_token = admin_response.json()["access_token"]

    student_response = client.post(
        "/auth/login",
        json={"username": STUDENT_USER["username"], "password": STUDENT_USER["password"]},
    )
    assert student_response.status_code == 200
    student_token = student_response.json()["access_token"]

    return {"admin": admin_token, "student": student_token}
