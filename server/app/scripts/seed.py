from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Exam, Question, User


USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "student1", "password": "student123", "role": "student"},
    {"username": "student2", "password": "student123", "role": "student"},
    {"username": "student3", "password": "student123", "role": "student"},
]



def seed_users(session) -> None:
    for u in USERS:
        existing = session.scalar(select(User).where(User.username == u["username"]))
        if existing:
            continue

        session.add(
            User(
                username=u["username"],
                password_hash=hash_password(u["password"]),
                role=u["role"],
            )
        )

"""
def seed_exam_with_questions(session):
    exam = session.scalar(select(Exam).where(Exam.exam_code == SAMPLE_EXAM["exam_code"]))
    if not exam:
        exam = Exam(**SAMPLE_EXAM)
        session.add(exam)
        session.flush()

    existing_questions = session.scalars(select(Question).where(Question.exam_id == exam.id)).all()
    existing_texts = {q.text for q in existing_questions}

    for qtext in QUESTIONS:
        if qtext in existing_texts:
            continue
        session.add(Question(exam_id=exam.id, text=qtext))

    return exam.id
"""

def main() -> None:
    with SessionLocal() as session:
        seed_users(session)
        #exam_id = seed_exam_with_questions(session)
        session.commit()

    print("Seeding complete.")
    #print(f"Sample exam UUID: {exam_id}")


if __name__ == "__main__":
    main()
