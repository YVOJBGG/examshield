import uuid
from secrets import randbelow

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Exam
from app.schemas.exam import ExamCreate, ExamUpdate


def list_exams(db: Session) -> list[Exam]:
    return list(db.scalars(select(Exam).order_by(Exam.created_at.desc())).all())


def _generate_unique_exam_code(db: Session) -> str:
    while True:
        exam_code = f"{randbelow(1_000_000):06d}"
        existing = db.scalar(select(Exam.id).where(Exam.exam_code == exam_code))
        if existing is None:
            return exam_code


def create_exam(db: Session, payload: ExamCreate) -> Exam:
    if payload.time_limit_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="time_limit_minutes must be greater than 0",
        )

    exam = Exam(
        exam_code=_generate_unique_exam_code(db),
        title=payload.title.strip(),
        time_limit_minutes=payload.time_limit_minutes,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def get_exam(db: Session, exam_id: uuid.UUID) -> Exam:
    exam = db.scalar(select(Exam).where(Exam.id == exam_id))
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


def update_exam(db: Session, exam_id: uuid.UUID, payload: ExamUpdate) -> Exam:
    exam = get_exam(db, exam_id)

    if payload.time_limit_minutes is not None and payload.time_limit_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="time_limit_minutes must be greater than 0",
        )

    if payload.title is not None:
        exam.title = payload.title.strip()
    if payload.time_limit_minutes is not None:
        exam.time_limit_minutes = payload.time_limit_minutes

    db.commit()
    db.refresh(exam)
    return exam


def delete_exam(db: Session, exam_id: uuid.UUID) -> None:
    exam = get_exam(db, exam_id)
    db.delete(exam)
    db.commit()
