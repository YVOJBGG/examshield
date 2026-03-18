import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Attempt, Violation
from app.schemas.monitoring import ViolationBroadcastOut


def _get_attempt_for_student(db: Session, attempt_id: uuid.UUID, user_id: uuid.UUID) -> Attempt:
    attempt = db.scalar(
        select(Attempt)
        .options(selectinload(Attempt.user), selectinload(Attempt.exam))
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


def _get_attempt_for_admin(db: Session, attempt_id: uuid.UUID) -> Attempt:
    attempt = db.scalar(select(Attempt).where(Attempt.id == attempt_id))
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return attempt


def create_violation(
    db: Session,
    *,
    user_id: uuid.UUID,
    attempt_id: uuid.UUID,
    violation_type: str,
    details: str | None,
) -> tuple[Violation, ViolationBroadcastOut]:
    attempt = _get_attempt_for_student(db, attempt_id, user_id)
    if attempt.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attempt is not active",
        )

    violation = Violation(
        attempt_id=attempt.id,
        type=violation_type,
        details=details,
    )
    db.add(violation)
    db.commit()
    db.refresh(violation)

    broadcast_payload = ViolationBroadcastOut(
        id=violation.id,
        attempt_id=violation.attempt_id,
        type=violation.type,
        details=violation.details,
        created_at=violation.created_at,
        username=attempt.user.username,
        exam_id=attempt.exam_id,
        status=attempt.status,
    )
    return violation, broadcast_payload


def list_attempt_violations(db: Session, attempt_id: uuid.UUID) -> list[Violation]:
    _get_attempt_for_admin(db, attempt_id)
    return list(
        db.scalars(
            select(Violation)
            .where(Violation.attempt_id == attempt_id)
            .order_by(Violation.created_at.desc())
        ).all()
    )
