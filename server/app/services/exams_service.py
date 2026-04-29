import uuid
from secrets import randbelow

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Exam, Question
from app.schemas.exam import ExamCreate, ExamUpdate


def _normalize_title(title: str) -> str:
    normalized = title.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title is required")
    return normalized


def _normalize_instructions(instructions: str | None) -> str | None:
    if instructions is None:
        return None
    normalized = instructions.strip()
    return normalized or None


def _validate_time_limit(time_limit_minutes: int) -> None:
    if time_limit_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="time_limit_minutes must be greater than 0",
        )


def list_exams(db: Session, admin_user_id: uuid.UUID) -> list[Exam]:
    return list(
        db.scalars(
            select(Exam)
            .where(Exam.created_by_user_id == admin_user_id)
            .order_by(Exam.created_at.desc())
        ).all()
    )


def _generate_unique_exam_code(db: Session) -> str:
    while True:
        exam_code = f"{randbelow(1_000_000):06d}"
        existing = db.scalar(select(Exam.id).where(Exam.exam_code == exam_code))
        if existing is None:
            return exam_code


def create_exam(db: Session, payload: ExamCreate, admin_user_id: uuid.UUID) -> Exam:
    _validate_time_limit(payload.time_limit_minutes)

    exam = Exam(
        exam_code=_generate_unique_exam_code(db),
        title=_normalize_title(payload.title),
        exam_type=payload.exam_type,
        instructions=_normalize_instructions(payload.instructions),
        time_limit_minutes=payload.time_limit_minutes,
        is_available=payload.is_available,
        created_by_user_id=admin_user_id,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def get_exam(db: Session, exam_id: uuid.UUID, admin_user_id: uuid.UUID | None = None) -> Exam:
    filters = [Exam.id == exam_id]
    if admin_user_id is not None:
        filters.append(Exam.created_by_user_id == admin_user_id)

    exam = db.scalar(
        select(Exam)
        .options(selectinload(Exam.questions).selectinload(Question.options))
        .where(*filters)
    )
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


def update_exam(db: Session, exam_id: uuid.UUID, payload: ExamUpdate, admin_user_id: uuid.UUID) -> Exam:
    exam = get_exam(db, exam_id, admin_user_id)

    if payload.time_limit_minutes is not None:
        _validate_time_limit(payload.time_limit_minutes)

    if payload.title is not None:
        exam.title = _normalize_title(payload.title)
    if payload.exam_type is not None:
        if payload.exam_type != exam.exam_type and exam.questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="exam_type cannot be changed after questions have been created",
            )
        exam.exam_type = payload.exam_type
    if payload.time_limit_minutes is not None:
        exam.time_limit_minutes = payload.time_limit_minutes
    if payload.instructions is not None:
        exam.instructions = _normalize_instructions(payload.instructions)
    if payload.is_available is not None:
        exam.is_available = payload.is_available

    db.commit()
    db.refresh(exam)
    return get_exam(db, exam_id, admin_user_id)


def delete_exam(db: Session, exam_id: uuid.UUID, admin_user_id: uuid.UUID) -> None:
    exam = get_exam(db, exam_id, admin_user_id)
    db.delete(exam)
    db.commit()
