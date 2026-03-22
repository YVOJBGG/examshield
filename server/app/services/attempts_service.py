import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Attempt, Exam, Question


def list_student_exams(db: Session) -> list[Exam]:
    return list(db.scalars(select(Exam).order_by(Exam.created_at.desc())).all())


def get_exam_for_student(db: Session, exam_code: str) -> Exam:
    exam = db.scalar(select(Exam).where(Exam.exam_code == exam_code))
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


def get_student_exam_content(db: Session, exam_code: str) -> tuple[Exam, list[Question]]:
    exam = get_exam_for_student(db, exam_code)
    questions = list(
        db.scalars(
            select(Question).where(Question.exam_id == exam.id).order_by(Question.created_at.asc())
        ).all()
    )
    return exam, questions


def start_attempt(db: Session, user_id: uuid.UUID, exam_code: str) -> Attempt:
    exam = get_exam_for_student(db, exam_code)

    existing = db.scalar(
        select(Attempt)
        .where(
            Attempt.user_id == user_id,
            Attempt.exam_id == exam.id,
            Attempt.status == "in_progress",
        )
        .order_by(Attempt.started_at.desc())
    )
    if existing is not None:
        return existing

    attempt = Attempt(user_id=user_id, exam_id=exam.id, status="in_progress")
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt
