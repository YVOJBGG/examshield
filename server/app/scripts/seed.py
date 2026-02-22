from passlib.context import CryptContext
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Exam, Question, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "student1", "password": "student123", "role": "student"},
    {"username": "student2", "password": "student123", "role": "student"},
    {"username": "student3", "password": "student123", "role": "student"},
]

EXAM_TITLE = "Milestone 1 Sample Exam"
QUESTIONS = [
    "What is the purpose of process isolation in operating systems?",
    "Explain ACID properties in transactional databases.",
    "Define normalization and list 1NF, 2NF, and 3NF briefly.",
    "What is the difference between authentication and authorization?",
    "Why do we use database migrations in backend projects?",
]


def seed_users(session) -> None:
    for u in USERS:
        existing = session.scalar(select(User).where(User.username == u["username"]))
        if existing:
            continue

        session.add(
            User(
                username=u["username"],
                password_hash=pwd_context.hash(u["password"]),
                role=u["role"],
            )
        )


def seed_exam_with_questions(session) -> None:
    exam = session.scalar(select(Exam).where(Exam.title == EXAM_TITLE))
    if not exam:
        exam = Exam(title=EXAM_TITLE, time_limit_minutes=60)
        session.add(exam)
        session.flush()

    existing_questions = session.scalars(select(Question).where(Question.exam_id == exam.id)).all()
    existing_texts = {q.text for q in existing_questions}

    for qtext in QUESTIONS:
        if qtext in existing_texts:
            continue
        session.add(Question(exam_id=exam.id, text=qtext))


def main() -> None:
    with SessionLocal() as session:
        seed_users(session)
        seed_exam_with_questions(session)
        session.commit()

    print("Seeding complete.")


if __name__ == "__main__":
    main()
