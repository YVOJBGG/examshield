import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_student
from app.db.session import get_db
from app.models import User
from app.schemas.violation import ViolationCreate, ViolationListItem, ViolationOut
from app.services.violations_service import create_violation, list_attempt_violations
from app.services.ws_manager import admin_monitoring_manager

router = APIRouter(prefix="/violations", tags=["violations"])


@router.post("", response_model=ViolationOut, status_code=status.HTTP_201_CREATED)
async def post_violation(
    payload: ViolationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
) -> ViolationOut:
    violation, broadcast_payload = create_violation(
        db,
        user_id=current_user.id,
        attempt_id=payload.attempt_id,
        violation_type=payload.type,
        details=payload.details,
    )
    await admin_monitoring_manager.broadcast_violation(broadcast_payload)
    return violation


@router.get("/attempt/{attempt_id}", response_model=list[ViolationListItem])
def get_attempt_violations(
    attempt_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[ViolationListItem]:
    return list_attempt_violations(db, attempt_id, current_user.id)
