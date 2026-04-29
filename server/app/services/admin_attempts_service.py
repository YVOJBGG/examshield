import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Answer, Attempt, Exam, Question
from app.schemas.review import (
    AttemptReviewAnswerItem,
    AttemptReviewDetail,
    AttemptReviewExam,
    AttemptReviewListItem,
    AttemptReviewOptionItem,
    AttemptReviewStudent,
)


def _grading_state(attempt: Attempt) -> str:
    if attempt.exam.exam_type == "mcq":
        return "auto_graded"
    if attempt.score is None:
        return "pending_manual_grading"
    return "manually_graded"


def _get_exam(db: Session, exam_id: uuid.UUID, admin_user_id: uuid.UUID) -> Exam:
    exam = db.scalar(select(Exam).where(Exam.id == exam_id, Exam.created_by_user_id == admin_user_id))
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


def _get_attempt(db: Session, attempt_id: uuid.UUID, admin_user_id: uuid.UUID) -> Attempt:
    attempt = db.scalar(
        select(Attempt)
        .options(
            selectinload(Attempt.user),
            selectinload(Attempt.exam),
            selectinload(Attempt.answers).selectinload(Answer.question).selectinload(Question.options),
        )
        .join(Attempt.exam)
        .where(Attempt.id == attempt_id, Exam.created_by_user_id == admin_user_id)
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return attempt


def list_submitted_attempts_for_exam(
    db: Session,
    exam_id: uuid.UUID,
    admin_user_id: uuid.UUID,
) -> list[AttemptReviewListItem]:
    _get_exam(db, exam_id, admin_user_id)
    attempts = list(
        db.scalars(
            select(Attempt)
            .options(selectinload(Attempt.user), selectinload(Attempt.exam))
            .where(Attempt.exam_id == exam_id, Attempt.status.in_(("submitted", "force_submitted")))
            .order_by(Attempt.submitted_at.desc(), Attempt.started_at.desc())
        ).all()
    )
    return [
        AttemptReviewListItem(
            attempt_id=item.id,
            username=item.user.username,
            status=item.status,
            started_at=item.started_at,
            submitted_at=item.submitted_at,
            score=item.score,
            grading_state=_grading_state(item),
        )
        for item in attempts
    ]


def get_attempt_review_detail(
    db: Session,
    attempt_id: uuid.UUID,
    admin_user_id: uuid.UUID,
) -> AttemptReviewDetail:
    attempt = _get_attempt(db, attempt_id, admin_user_id)
    if attempt.status not in {"submitted", "force_submitted"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed attempts can be reviewed",
        )

    questions = list(
        db.scalars(
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.exam_id == attempt.exam_id)
            .order_by(Question.order_index.asc(), Question.created_at.asc())
        ).all()
    )
    answers_by_question = {answer.question_id: answer for answer in attempt.answers}
    answer_items: list[AttemptReviewAnswerItem] = []

    for question in questions:
        answer = answers_by_question.get(question.id)
        selected_option_ids = answer.selected_option_ids or [] if answer is not None else []
        is_correct = None
        awarded_points = None

        if attempt.exam.exam_type == "mcq":
            correct_ids = {str(option.id) for option in question.options if option.is_correct}
            is_correct = set(selected_option_ids) == correct_ids
            awarded_points = question.points if is_correct else 0.0

        answer_items.append(
            AttemptReviewAnswerItem(
                question_id=question.id,
                question_text=question.text,
                points=question.points,
                order_index=question.order_index,
                answer_text=answer.answer_text if answer is not None else None,
                selected_option_ids=selected_option_ids,
                options=[
                    AttemptReviewOptionItem(
                        id=option.id,
                        option_text=option.option_text,
                        order_index=option.order_index,
                        is_correct=option.is_correct,
                    )
                    for option in question.options
                ],
                is_correct=is_correct,
                awarded_points=awarded_points,
            )
        )

    return AttemptReviewDetail(
        attempt_id=attempt.id,
        status=attempt.status,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        score=attempt.score,
        graded_at=attempt.graded_at,
        grading_state=_grading_state(attempt),
        student=AttemptReviewStudent(id=attempt.user.id, username=attempt.user.username),
        exam=AttemptReviewExam(
            id=attempt.exam.id,
            exam_code=attempt.exam.exam_code,
            title=attempt.exam.title,
            exam_type=attempt.exam.exam_type,
            instructions=attempt.exam.instructions,
        ),
        answers=answer_items,
    )


def update_attempt_score(db: Session, attempt_id: uuid.UUID, score: float, admin_user_id: uuid.UUID) -> Attempt:
    attempt = _get_attempt(db, attempt_id, admin_user_id)
    if attempt.status not in {"submitted", "force_submitted"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed attempts can be graded",
        )
    if attempt.exam.exam_type != "written":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only written exam attempts can be graded manually",
        )

    attempt.score = score
    attempt.graded_at = datetime.now(timezone.utc)
    attempt.graded_by_user_id = admin_user_id
    db.commit()
    db.refresh(attempt)
    return attempt
