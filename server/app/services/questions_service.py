import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Exam, Question, QuestionOption
from app.schemas.question import QuestionCreate, QuestionOptionCreate, QuestionUpdate
from app.services.exams_service import get_exam


def _normalize_question_text(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question text cannot be empty")
    return normalized


def _validate_points(points: float) -> float:
    if points <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="points must be greater than 0")
    return points


def _validate_order_index(order_index: int) -> int:
    if order_index < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="order_index cannot be negative")
    return order_index


def _next_order_index(db: Session, exam_id: uuid.UUID) -> int:
    current_max = db.scalar(select(func.max(Question.order_index)).where(Question.exam_id == exam_id))
    return 0 if current_max is None else current_max + 1


def _normalize_mcq_options(options: list[QuestionOptionCreate]) -> list[dict[str, object]]:
    if len(options) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MCQ questions must include at least 2 options",
        )

    normalized: list[dict[str, object]] = []
    correct_count = 0
    for index, option in enumerate(options):
        option_text = option.option_text.strip()
        if not option_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MCQ option text cannot be empty",
            )
        is_correct = bool(option.is_correct)
        if is_correct:
            correct_count += 1
        normalized.append(
            {
                "option_text": option_text,
                "is_correct": is_correct,
                "order_index": _validate_order_index(option.order_index) if option.order_index is not None else index,
            }
        )

    if correct_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MCQ questions must include at least 1 correct option",
        )
    if correct_count != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MCQ questions must include exactly 1 correct option in v1",
        )

    return normalized


def _sync_question_options(question: Question, exam: Exam, options: list[QuestionOptionCreate] | None) -> None:
    if exam.exam_type == "written":
        if options:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Written exam questions cannot include MCQ options",
            )
        question.options.clear()
        return

    if options is None:
        if not question.options:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MCQ questions must include options",
            )
        return

    normalized_options = _normalize_mcq_options(options)
    question.options.clear()
    for item in normalized_options:
        question.options.append(
            QuestionOption(
                option_text=item["option_text"],
                is_correct=item["is_correct"],
                order_index=item["order_index"],
            )
        )


def list_questions(db: Session, exam_id: uuid.UUID) -> list[Question]:
    get_exam(db, exam_id)
    stmt = (
        select(Question)
        .options(selectinload(Question.options))
        .where(Question.exam_id == exam_id)
        .order_by(Question.order_index.asc(), Question.created_at.asc())
    )
    return list(db.scalars(stmt).all())


def create_question(db: Session, exam_id: uuid.UUID, payload: QuestionCreate) -> Question:
    exam = get_exam(db, exam_id)

    question = Question(
        exam_id=exam_id,
        text=_normalize_question_text(payload.text),
        points=_validate_points(payload.points),
        order_index=_validate_order_index(payload.order_index)
        if payload.order_index is not None
        else _next_order_index(db, exam_id),
    )
    _sync_question_options(question, exam, payload.options)

    db.add(question)
    db.commit()
    db.refresh(question)
    return get_question(db, exam_id, question.id)


def get_question(db: Session, exam_id: uuid.UUID, question_id: uuid.UUID) -> Question:
    get_exam(db, exam_id)
    question = db.scalar(
        select(Question)
        .options(selectinload(Question.options))
        .where(Question.id == question_id, Question.exam_id == exam_id)
    )
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question


def update_question(
    db: Session, exam_id: uuid.UUID, question_id: uuid.UUID, payload: QuestionUpdate
) -> Question:
    exam = get_exam(db, exam_id)
    question = get_question(db, exam_id, question_id)

    if payload.text is not None:
        question.text = _normalize_question_text(payload.text)
    if payload.points is not None:
        question.points = _validate_points(payload.points)
    if payload.order_index is not None:
        question.order_index = _validate_order_index(payload.order_index)

    _sync_question_options(question, exam, payload.options)

    db.commit()
    db.refresh(question)
    return get_question(db, exam_id, question_id)


def delete_question(db: Session, exam_id: uuid.UUID, question_id: uuid.UUID) -> None:
    question = get_question(db, exam_id, question_id)
    db.delete(question)
    db.commit()
