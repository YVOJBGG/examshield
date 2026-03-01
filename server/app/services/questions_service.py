import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Question
from app.schemas.question import QuestionCreate, QuestionUpdate
from app.services.exams_service import get_exam


def list_questions(db: Session, exam_id: uuid.UUID) -> list[Question]:
    get_exam(db, exam_id)
    stmt = select(Question).where(Question.exam_id == exam_id).order_by(Question.created_at.asc())
    return list(db.scalars(stmt).all())


def create_question(db: Session, exam_id: uuid.UUID, payload: QuestionCreate) -> Question:
    get_exam(db, exam_id)

    if not payload.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question text cannot be empty")

    question = Question(exam_id=exam_id, text=payload.text.strip())
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def get_question(db: Session, exam_id: uuid.UUID, question_id: uuid.UUID) -> Question:
    get_exam(db, exam_id)
    question = db.scalar(
        select(Question).where(Question.id == question_id, Question.exam_id == exam_id)
    )
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question


def update_question(
    db: Session, exam_id: uuid.UUID, question_id: uuid.UUID, payload: QuestionUpdate
) -> Question:
    question = get_question(db, exam_id, question_id)

    if payload.text is not None:
        if not payload.text.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question text cannot be empty")
        question.text = payload.text.strip()

    db.commit()
    db.refresh(question)
    return question


def delete_question(db: Session, exam_id: uuid.UUID, question_id: uuid.UUID) -> None:
    question = get_question(db, exam_id, question_id)
    db.delete(question)
    db.commit()
