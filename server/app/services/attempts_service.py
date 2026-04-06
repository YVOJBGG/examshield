import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Attempt, Exam, Question


def list_student_exams(db: Session) -> list[Exam]:
    return list(db.scalars(select(Exam).order_by(Exam.created_at.desc())).all())


def get_exam_for_student(db: Session, exam_code: str) -> Exam:
    exam = db.scalar(select(Exam).where(Exam.exam_code == exam_code))
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


def _get_submitted_attempt(db: Session, user_id: uuid.UUID, exam_id: uuid.UUID) -> Attempt | None:
    return db.scalar(
        select(Attempt)
        .where(
            Attempt.user_id == user_id,
            Attempt.exam_id == exam_id,
            Attempt.status.in_(("submitted", "force_submitted")),
        )
        .order_by(Attempt.started_at.desc())
    )


def _get_in_progress_attempt(db: Session, user_id: uuid.UUID, exam_id: uuid.UUID) -> Attempt | None:
    return db.scalar(
        select(Attempt)
        .where(
            Attempt.user_id == user_id,
            Attempt.exam_id == exam_id,
            Attempt.status == "in_progress",
        )
        .order_by(Attempt.started_at.desc())
    )


def _validate_student_exam_entry(db: Session, user_id: uuid.UUID, exam: Exam) -> Attempt | None:
    submitted_attempt = _get_submitted_attempt(db, user_id, exam.id)
    if submitted_attempt is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted this exam and cannot re-enter it.",
        )

    in_progress_attempt = _get_in_progress_attempt(db, user_id, exam.id)
    if in_progress_attempt is not None:
        return in_progress_attempt

    if exam.is_ended:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This exam has already ended.",
        )

    if not exam.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This exam is currently unavailable.",
        )

    return None


def get_student_exam_content(db: Session, user_id: uuid.UUID, exam_code: str) -> tuple[Exam, list[Question]]:
    exam = get_exam_for_student(db, exam_code)
    _validate_student_exam_entry(db, user_id, exam)
    questions = list(
        db.scalars(
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.exam_id == exam.id)
            .order_by(Question.order_index.asc(), Question.created_at.asc())
        ).all()
    )
    return exam, questions


def start_attempt(db: Session, user_id: uuid.UUID, exam_code: str) -> Attempt:
    exam = get_exam_for_student(db, exam_code)
    existing = _validate_student_exam_entry(db, user_id, exam)
    if existing is not None:
        return existing

    attempt = Attempt(user_id=user_id, exam_id=exam.id, status="in_progress")
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt
