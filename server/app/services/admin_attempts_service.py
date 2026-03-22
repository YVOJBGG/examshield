import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Answer, Attempt, Exam, Question, User
from app.schemas.review import (
    AttemptReviewAnswerItem,
    AttemptReviewDetail,
    AttemptReviewExam,
    AttemptReviewListItem,
    AttemptReviewStudent,
)


def _get_exam(db: Session, exam_id: uuid.UUID) -> Exam:
    exam = db.scalar(select(Exam).where(Exam.id == exam_id))
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


def _get_attempt(db: Session, attempt_id: uuid.UUID) -> Attempt:
    attempt = db.scalar(
        select(Attempt)
        .options(
            selectinload(Attempt.user),
            selectinload(Attempt.exam),
            selectinload(Attempt.answers).selectinload(Answer.question),
        )
        .where(Attempt.id == attempt_id)
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return attempt


def list_submitted_attempts_for_exam(db: Session, exam_id: uuid.UUID) -> list[AttemptReviewListItem]:
    _get_exam(db, exam_id)
    attempts = list(
        db.scalars(
            select(Attempt)
            .options(selectinload(Attempt.user))
            .where(Attempt.exam_id == exam_id, Attempt.status == "submitted")
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
        )
        for item in attempts
    ]


def get_attempt_review_detail(db: Session, attempt_id: uuid.UUID) -> AttemptReviewDetail:
    attempt = _get_attempt(db, attempt_id)
    if attempt.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only submitted attempts can be reviewed",
        )

    questions = list(
        db.scalars(
            select(Question).where(Question.exam_id == attempt.exam_id).order_by(Question.created_at.asc())
        ).all()
    )
    answers_by_question = {answer.question_id: answer for answer in attempt.answers}
    answer_items = [
        AttemptReviewAnswerItem(
            question_id=question.id,
            question_text=question.text,
            answer_text=answers_by_question.get(question.id).answer_text
            if answers_by_question.get(question.id) is not None
            else None,
        )
        for question in questions
    ]

    return AttemptReviewDetail(
        attempt_id=attempt.id,
        status=attempt.status,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        score=attempt.score,
        graded_at=attempt.graded_at,
        student=AttemptReviewStudent(id=attempt.user.id, username=attempt.user.username),
        exam=AttemptReviewExam(
            id=attempt.exam.id,
            exam_code=attempt.exam.exam_code,
            title=attempt.exam.title,
        ),
        answers=answer_items,
    )


def update_attempt_score(db: Session, attempt_id: uuid.UUID, score: float, admin_user_id: uuid.UUID) -> Attempt:
    attempt = _get_attempt(db, attempt_id)
    if attempt.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only submitted attempts can be graded",
        )

    attempt.score = score
    attempt.graded_at = datetime.now(timezone.utc)
    attempt.graded_by_user_id = admin_user_id
    db.commit()
    db.refresh(attempt)
    return attempt
