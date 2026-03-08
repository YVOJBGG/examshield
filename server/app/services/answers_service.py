import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Answer, Attempt, Question
from app.schemas.answer import AnswerAutosaveItem


def _get_attempt_for_student(db: Session, attempt_id: uuid.UUID, user_id: uuid.UUID) -> Attempt:
    attempt = db.scalar(select(Attempt).where(Attempt.id == attempt_id))
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    if attempt.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Attempt does not belong to current student",
        )
    return attempt


def _validate_attempt_in_progress(attempt: Attempt, error_detail: str) -> None:
    if attempt.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail)


def _validate_questions_for_exam(
    db: Session, exam_id: uuid.UUID, items: list[AnswerAutosaveItem]
) -> set[uuid.UUID]:
    question_ids = {item.question_id for item in items}
    if not question_ids:
        return set()

    valid_ids = set(
        db.scalars(
            select(Question.id).where(Question.exam_id == exam_id, Question.id.in_(question_ids))
        ).all()
    )
    missing = question_ids - valid_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more questions do not belong to this exam",
        )
    return question_ids


def _upsert_answers(
    db: Session, attempt_id: uuid.UUID, items: list[AnswerAutosaveItem], question_ids: set[uuid.UUID]
) -> list[Answer]:
    if not question_ids:
        return []

    existing_answers = list(
        db.scalars(
            select(Answer).where(Answer.attempt_id == attempt_id, Answer.question_id.in_(question_ids))
        ).all()
    )
    by_question_id = {row.question_id: row for row in existing_answers}
    now = datetime.now(timezone.utc)

    for item in items:
        row = by_question_id.get(item.question_id)
        if row is None:
            row = Answer(
                attempt_id=attempt_id,
                question_id=item.question_id,
                answer_text=item.answer_text,
                saved_at=now,
            )
            db.add(row)
            by_question_id[item.question_id] = row
            continue
        row.answer_text = item.answer_text
        row.saved_at = now

    db.flush()
    return list(by_question_id.values())


def autosave_answers(
    db: Session, user_id: uuid.UUID, attempt_id: uuid.UUID, items: list[AnswerAutosaveItem]
) -> list[Answer]:
    attempt = _get_attempt_for_student(db, attempt_id, user_id)
    _validate_attempt_in_progress(attempt, "Attempt already submitted")

    question_ids = _validate_questions_for_exam(db, attempt.exam_id, items)
    saved_answers = _upsert_answers(db, attempt.id, items, question_ids)
    db.commit()
    return saved_answers


def submit_answers(
    db: Session, user_id: uuid.UUID, attempt_id: uuid.UUID, items: list[AnswerAutosaveItem]
) -> tuple[Attempt, int]:
    attempt = _get_attempt_for_student(db, attempt_id, user_id)
    _validate_attempt_in_progress(attempt, "Attempt already submitted")

    question_ids = _validate_questions_for_exam(db, attempt.exam_id, items)
    saved_answers = _upsert_answers(db, attempt.id, items, question_ids)

    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(attempt)
    return attempt, len(saved_answers)
