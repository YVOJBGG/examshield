import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Answer, Attempt, Question
from app.schemas.answer import AnswerAutosaveItem


def _get_attempt_for_student(db: Session, attempt_id: uuid.UUID, user_id: uuid.UUID) -> Attempt:
    attempt = db.scalar(
        select(Attempt)
        .options(
            selectinload(Attempt.exam),
            selectinload(Attempt.answers),
        )
        .where(Attempt.id == attempt_id)
    )
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
) -> dict[uuid.UUID, Question]:
    question_ids = {item.question_id for item in items}
    if not question_ids:
        return {}

    questions = list(
        db.scalars(
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.exam_id == exam_id, Question.id.in_(question_ids))
        ).all()
    )
    questions_by_id = {question.id: question for question in questions}
    missing = question_ids - set(questions_by_id)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more questions do not belong to this exam",
        )
    return questions_by_id


def _normalize_written_answer(item: AnswerAutosaveItem) -> str:
    if item.answer_text is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Written answers require answer_text",
        )
    if item.selected_option_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Written answers cannot include selected_option_ids",
        )
    return item.answer_text.strip()


def _normalize_selected_option_ids(question: Question, item: AnswerAutosaveItem) -> list[str]:
    if item.answer_text not in (None, ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MCQ answers cannot include answer_text",
        )
    valid_option_ids = {str(option.id) for option in question.options}
    normalized: list[str] = []
    seen: set[str] = set()

    for option_id in item.selected_option_ids:
        option_id_str = str(option_id)
        if option_id_str not in valid_option_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more selected options do not belong to this question",
            )
        if option_id_str in seen:
            continue
        seen.add(option_id_str)
        normalized.append(option_id_str)

    return normalized


def _upsert_answers(
    db: Session,
    attempt: Attempt,
    items: list[AnswerAutosaveItem],
    questions_by_id: dict[uuid.UUID, Question],
) -> list[Answer]:
    if not questions_by_id:
        return []

    existing_answers = {
        row.question_id: row
        for row in db.scalars(
            select(Answer).where(Answer.attempt_id == attempt.id, Answer.question_id.in_(questions_by_id))
        ).all()
    }
    now = datetime.now(timezone.utc)

    for item in items:
        question = questions_by_id[item.question_id]
        row = existing_answers.get(item.question_id)
        if row is None:
            row = Answer(attempt_id=attempt.id, question_id=item.question_id)
            db.add(row)
            existing_answers[item.question_id] = row

        if attempt.exam.exam_type == "written":
            row.answer_text = _normalize_written_answer(item)
            row.selected_option_ids = []
        else:
            row.answer_text = None
            row.selected_option_ids = _normalize_selected_option_ids(question, item)
        row.saved_at = now

    db.flush()
    return list(existing_answers.values())


def _calculate_mcq_score(questions_by_id: dict[uuid.UUID, Question], saved_answers: list[Answer]) -> float:
    answers_by_question = {answer.question_id: answer for answer in saved_answers}
    total = 0.0

    for question in questions_by_id.values():
        correct_ids = {str(option.id) for option in question.options if option.is_correct}
        selected_ids = set(answers_by_question.get(question.id).selected_option_ids or []) if question.id in answers_by_question else set()
        if selected_ids == correct_ids:
            total += question.points

    return total


def _load_exam_questions(db: Session, exam_id: uuid.UUID) -> dict[uuid.UUID, Question]:
    questions = list(
        db.scalars(
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.exam_id == exam_id)
        ).all()
    )
    return {question.id: question for question in questions}


def autosave_answers(
    db: Session, user_id: uuid.UUID, attempt_id: uuid.UUID, items: list[AnswerAutosaveItem]
) -> list[Answer]:
    attempt = _get_attempt_for_student(db, attempt_id, user_id)
    _validate_attempt_in_progress(attempt, "Attempt already submitted")

    questions_by_id = _validate_questions_for_exam(db, attempt.exam_id, items)
    saved_answers = _upsert_answers(db, attempt, items, questions_by_id)
    db.commit()
    return saved_answers


def submit_answers(
    db: Session, user_id: uuid.UUID, attempt_id: uuid.UUID, items: list[AnswerAutosaveItem]
) -> tuple[Attempt, int]:
    attempt = _get_attempt_for_student(db, attempt_id, user_id)
    _validate_attempt_in_progress(attempt, "Attempt already submitted")

    questions_by_id = _validate_questions_for_exam(db, attempt.exam_id, items)
    saved_answers = _upsert_answers(db, attempt, items, questions_by_id)

    submitted_at = datetime.now(timezone.utc)
    attempt.status = "submitted"
    attempt.submitted_at = submitted_at

    if attempt.exam.exam_type == "mcq":
        all_questions_by_id = _load_exam_questions(db, attempt.exam_id)
        all_saved_answers = list(
            db.scalars(select(Answer).where(Answer.attempt_id == attempt.id)).all()
        )
        attempt.score = _calculate_mcq_score(all_questions_by_id, all_saved_answers)
        attempt.graded_at = submitted_at
        attempt.graded_by_user_id = None
    else:
        attempt.score = None
        attempt.graded_at = None
        attempt.graded_by_user_id = None

    db.commit()
    db.refresh(attempt)
    return attempt, len(saved_answers)
