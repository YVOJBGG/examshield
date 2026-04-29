import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models import User
from app.schemas.exam_analytics import ExamAnalyticsResponse, ExamEndResponse
from app.schemas.review import AttemptReviewDetail, AttemptReviewListItem, AttemptScoreOut, AttemptScoreUpdate
from app.services.admin_attempts_service import (
    get_attempt_review_detail,
    list_submitted_attempts_for_exam,
    update_attempt_score,
)
from app.services.exam_analytics_service import end_exam, get_exam_analytics

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
def admin_ping(_: User = Depends(require_admin)) -> dict[str, str]:
    return {"status": "ok", "message": "admin pong"}


@router.get("/exams/{exam_id}/attempts", response_model=list[AttemptReviewListItem])
def get_exam_attempts(
    exam_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[AttemptReviewListItem]:
    return list_submitted_attempts_for_exam(db, exam_id, current_user.id)


@router.post("/exams/{exam_id}/end", response_model=ExamEndResponse)
def post_end_exam(
    exam_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ExamEndResponse:
    return end_exam(db, exam_id, current_user.id)


@router.get(
    "/exams/{exam_id}/analytics",
    response_model=ExamAnalyticsResponse,
    response_model_exclude_none=True,
)
def get_exam_analytics_endpoint(
    exam_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ExamAnalyticsResponse:
    return get_exam_analytics(db, exam_id, current_user.id)


@router.get("/attempts/{attempt_id}", response_model=AttemptReviewDetail)
def get_attempt_detail(
    attempt_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AttemptReviewDetail:
    return get_attempt_review_detail(db, attempt_id, current_user.id)


@router.put("/attempts/{attempt_id}/score", response_model=AttemptScoreOut)
def put_attempt_score(
    attempt_id: uuid.UUID,
    payload: AttemptScoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AttemptScoreOut:
    return update_attempt_score(db, attempt_id, payload.score, current_user.id)
