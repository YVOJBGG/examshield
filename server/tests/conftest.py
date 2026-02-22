import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models import User

USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "student1", "password": "student123", "role": "student"},
]


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
